package tpu_complete // 💡 핵심: 기존 코드와 이름이 겹치지 않게 격리하는 마법의 명령어

import chisel3._
import chisel3.util._

// =====================================================================
// [1] 가속기 내부 전송용 데이터 흐름 인터페이스 (Bundle)
// =====================================================================
// 시스톨릭 어레이 내부에서 데이터가 동서남북으로 흐르는 물리적 길(Wire)을 정의합니다.
class SystolicIO extends Bundle {
  val west_in_a   = Input(UInt(8.W))   // 왼쪽에서 들어오는 Activation (입력 행렬 A)
  val east_out_a  = Output(UInt(8.W))  // 오른쪽으로 나가는 Activation (다음 PE로 전달)
  val north_in_c  = Input(UInt(16.W))  // 위에서 내려오는 Partial Sum (부분합 C)
  val south_out_c = Output(UInt(16.W)) // 아래로 내려보내는 Partial Sum (누적된 부분합)
}

// =====================================================================
// [2] Data Orchestration Unit (데이터 지휘 컨트롤러)
// =====================================================================
// 외부 메모리에서 들어온 2D 데이터를 시스톨릭 어레이의 타이밍에 맞게 
// 대각선(Diagonal Wavefront) 형태로 비틀어주는(Skewing) 전용 모듈입니다.
class MyDataOrchUnit extends Module {
  val io = IO(new Bundle {
    val in_input      = Input(Vec(16, UInt(8.W))) // 외부에서 들어오는 정방형 입력 A
    val in_weight     = Input(Vec(16, UInt(8.W))) // 외부에서 들어오는 정방형 가중치 W
    val feed_enable   = Input(Bool())             // 데이터 주입 시작 제어
    val load_enable   = Input(Bool())             // 가중치 장전 제어
    
    val skewed_input  = Output(Vec(16, UInt(8.W))) // 찌그러진(지연된) 입력 A 출력
    val skewed_weight = Output(Vec(16, UInt(8.W))) // 가중치 W 출력 (지연 불필요)
    val skewed_load_w = Output(Vec(16, Bool()))    // 대각선 타이밍에 맞춘 장전 신호 출력
  })

  // 핵심: 각 Row(r)마다 r클럭만큼 물리적으로 지연시켜 사선 파도(Wavefront)를 형성합니다.
  for (r <- 0 until 16) {
    // 0번 행은 0클럭, 1번 행은 1클럭 ... 15번 행은 15클럭 지연
    io.skewed_input(r)  := ShiftRegister(io.in_input(r), r, 0.U, io.feed_enable)
    io.skewed_weight(r) := io.in_weight(r) // 가중치는 그대로 하강
    io.skewed_load_w(r) := ShiftRegister(io.load_enable, r, false.B) // 장전 신호도 사선으로 맞춤
  }
}

// =====================================================================
// [3] 단일 MAC Unit (Double Buffering 탑재형 연산 세포)
// =====================================================================
// 행렬 곱셈을 수행하는 가장 작은 단위이며, 연산 지연을 막는 섀도우 버퍼를 가집니다.
class MyMacUnit extends Module {
  val io = IO(new Bundle {
    val data      = new SystolicIO()
    val weight_in = Input(UInt(8.W)) 
    val load_w    = Input(Bool())    // Shadow 대기실 장전 신호 (백그라운드 로드)
    val swap_w    = Input(Bool())    // Active 무대 즉시 전환 신호 (1클럭 스위칭)
  })
  
  // Double Buffering 구현용 레지스터
  val weight_shadow = RegInit(0.U(8.W)) // 백그라운드 대기실
  val weight_active = RegInit(0.U(8.W)) // 현재 연산에 참여하는 무대

  when(io.load_w) { weight_shadow := io.weight_in }
  when(io.swap_w) { weight_active := weight_shadow }

  // 핵심 행렬 곱셈 연산 회로: (A * W) + C
  val mac_result = (io.data.west_in_a * weight_active) + io.data.north_in_c
  
  // 파이프라인 매칭: 연산 결과와 입력값을 1클럭 뒤에 이웃 PE로 전달 (RegNext)
  io.data.south_out_c := RegNext(mac_result)
  io.data.east_out_a  := RegNext(io.data.west_in_a)
}

// =====================================================================
// [4] 누산기 (Accumulator + Bias Addition)
// =====================================================================
// 16-bit 부분합을 32-bit로 확장하여 오버플로우를 막고, Bias(편향)를 처리합니다.
class MyAccumBufferChannel extends Module {
  val io = IO(new Bundle {
    val in_mac_result = Input(UInt(16.W)) // MXU 바닥에서 떨어지는 16-bit 부분합
    val bias_in       = Input(UInt(32.W)) // 외부 주입 편향(Bias) 값
    val bias_load     = Input(Bool())     // Bias 값을 누산 버퍼 기저에 로드하는 신호
    val accum_en      = Input(Bool())     // 타일 누산 활성화 제어 신호
    val clear         = Input(Bool())     // 전체 초기화 신호
    val out_accum     = Output(UInt(32.W))// VPU로 뻗어나가는 최종 32-bit 결과
  })
  
  // 16개의 타일을 회전하며 누적하기 위한 시프트 레지스터 뱅크
  val shift_reg = RegInit(VecInit(Seq.fill(16)(0.U(32.W))))
  
  // 기존 누적값 + 새로 들어온 부분합(16-bit -> 32-bit로 확장)
  val current_sum = shift_reg(0) + io.in_mac_result.zext.asUInt

  when(io.clear) {
    for (i <- 0 until 16) { shift_reg(i) := 0.U }
  }.elsewhen(io.bias_load) {
    // 💡 최적화 포인트: 연산 시작 전 Bias 값을 바닥에 깔아 자연스러운 A*W+B 연산 유도
    shift_reg(15) := io.bias_in
    for (i <- 0 until 15) { shift_reg(i) := shift_reg(i + 1) }
  }.elsewhen(io.accum_en) {
    shift_reg(15) := current_sum
    for (i <- 0 until 15) { shift_reg(i) := shift_reg(i + 1) }
  }
  
  io.out_accum := shift_reg(0)
}

// =====================================================================
// [5] VPU 1단계: 양자화 스케일러 및 활성화 LUT 코어 (QuantActCore)
// =====================================================================
class MyQuantActCore extends Module {
  val io = IO(new Bundle {
    val in_mac      = Input(UInt(32.W))  // Accumulator에서 온 32-bit 값
    val param       = Input(UInt(32.W))  // 양자화 스케일 파라미터 [M, S, ZP]
    val act_en      = Input(Bool())      // true: LUT 활성화, false: 선형 양자화
    val lut_wr_en   = Input(Bool())      // FPGA BRAM(LUT) 쓰기 제어
    val lut_wr_addr = Input(UInt(10.W))
    val lut_wr_data = Input(UInt(8.W))
    val out_qact    = Output(UInt(8.W))  // 최종 8-bit INT8 출력
  })
  
  val zp    = io.param(7, 0).asSInt
  val shift = io.param(12, 8).asUInt
  val mult  = io.param(31, 16).asUInt

  // 하드웨어 양자화 수식: ((Input - ZP) * M) >> S
  val sub_res  = io.in_mac.asSInt.pad(33) - zp.pad(33)
  val mult_res = sub_res * mult.zext.asSInt
  val shift_res_10b   = (mult_res >> (shift - 2.U)).asSInt
  
  // 10-bit 범위 클램핑 (0 ~ 1023 이탈 방어)
  val clamped_idx_10b = Mux(shift_res_10b < 0.S, 0.U(10.W), Mux(shift_res_10b > 1023.S, 1023.U(10.W), shift_res_10b(9, 0).asUInt))

  // 1024-Entry 내장 FPGA BRAM(LUT) 블록 생성
  val act_lut_bram = Mem(1024, UInt(8.W))
  when(io.lut_wr_en) { act_lut_bram(io.lut_wr_addr) := io.lut_wr_data }
  
  val lut_out = act_lut_bram(clamped_idx_10b)
  val linear_8b_out = clamped_idx_10b(9, 2) // 선형 다운스케일링 바이패스
  
  // 1클럭 지연 파이프라인 매칭
  io.out_qact := Mux(RegNext(io.act_en), lut_out, RegNext(linear_8b_out))
}

// =====================================================================
// [6] VPU 2단계: 실시간 정규화 라인 모듈 (NormLine)
// =====================================================================
class MyUniversalNormLine extends Module {
  val io = IO(new Bundle {
    val stream_in      = Input(UInt(8.W))
    val stream_valid   = Input(Bool())
    val mode_sel       = Input(UInt(2.W)) // 0: RMSNorm, 1: LayerNorm
    val clr_acc        = Input(Bool())
    val out_data       = Output(UInt(8.W))
    val out_valid      = Output(Bool())
  })
  
  // 실시간(On-the-fly) 하드웨어 통계량 추적 레지스터
  val sum1_reg = RegInit(0.U(32.W)) // 데이터의 합
  val sum2_reg = RegInit(0.U(32.W)) // 데이터의 제곱합
  
  when(io.clr_acc) {
    sum1_reg := 0.U; sum2_reg := 0.U
  }.elsewhen(io.stream_valid) {
    sum1_reg := sum1_reg + io.stream_in.zext.asUInt
    sum2_reg := sum2_reg + (io.stream_in * io.stream_in)
  }

  // 수학적 분산 유도 회로: Var = E[X^2] - (E[X])^2
  val mu_wire = sum1_reg >> 12 
  val var_algebraic = (sum2_reg >> 12) - (mu_wire * mu_wire) 
  val final_reduction = Mux(io.mode_sel === 1.U, var_algebraic, (sum2_reg >> 12))

  // 우선순위 인코더 기반 스케일 팩터 추출 (나눗셈을 비트 시프트로 근사화)
  val lz_count = PriorityEncoder(final_reduction.asBools.reverse)
  val norm_res = (io.stream_in.zext.asUInt << (lz_count(2,0))) 
  
  // 8-bit 오버플로우 방지 및 파이프라인 지연 매칭
  io.out_data  := Mux(norm_res > 255.U, 255.U(8.W), norm_res(7, 0))
  io.out_valid := RegNext(io.stream_valid)
}

// =====================================================================
// [7] 최종 완성형 Top Module (모듈 간 완벽한 분리 및 결합)
// =====================================================================
class MyTPU_Complete_Top extends Module {
  val io = IO(new Bundle {
    val in_input        = Input(Vec(16, UInt(8.W)))
    val in_weight       = Input(Vec(16, UInt(8.W)))
    val in_bias         = Input(Vec(16, UInt(32.W)))
    
    val feed_enable     = Input(Bool())
    val load_enable     = Input(Bool())
    val swap_weights    = Input(Bool())
    val bias_load       = Input(Bool()) 
    val accum_en        = Input(Bool())
    val clear_all       = Input(Bool())
    
    val act_mode_en     = Input(Bool())
    val norm_mode_sel   = Input(UInt(2.W))
    
    val final_post_out  = Output(Vec(16, UInt(8.W))) // 최종 정제된 아웃풋
    val final_valid     = Output(Vec(16, Bool()))
  })

  // 1. 하드웨어 블록 컴포넌트 실체화 배치
  val orchestrator = Module(new MyDataOrchUnit()) // 분리된 외부 지휘관 탑재
  val mxu          = Seq.fill(16, 16)(Module(new MyMacUnit())) // 16x16 어레이
  val accumulators = Seq.fill(16)(Module(new MyAccumBufferChannel()))
  val quant_cores  = Seq.fill(16)(Module(new MyQuantActCore()))
  val norm_lines   = Seq.fill(16)(Module(new MyUniversalNormLine()))

  // 2. 외부 핀 -> Orchestrator 연결
  orchestrator.io.in_input    := io.in_input
  orchestrator.io.in_weight   := io.in_weight
  orchestrator.io.feed_enable := io.feed_enable
  orchestrator.io.load_enable := io.load_enable

  // 3. Orchestrator -> 16x16 시스톨릭 어레이 메시 배선 연결
  for (r <- 0 until 16) {
    for (c <- 0 until 16) {
      // 💡 Orchestrator가 대각선(Wavefront)으로 타이밍을 맞춘 신호를 주입합니다.
      mxu(r)(c).io.weight_in := orchestrator.io.skewed_weight(c)
      mxu(r)(c).io.load_w    := orchestrator.io.skewed_load_w(r)
      mxu(r)(c).io.swap_w    := io.swap_weights
      
      // 맨 왼쪽 열(c=0)에는 Orchestrator가 찌그러뜨린(Skewed) 입력을 투입
      if (c == 0) mxu(r)(0).io.data.west_in_a := orchestrator.io.skewed_input(r)
      else        mxu(r)(c).io.data.west_in_a := mxu(r)(c - 1).io.data.east_out_a
      
      if (r == 0) mxu(0)(c).io.data.north_in_c := 0.U
      else        mxu(r)(c).io.data.north_in_c := mxu(r - 1)(c).io.data.south_out_c
    }
  }

  // 4. MXU 아랫단 -> VPU 파이프라인 결합
  for (c <- 0 until 16) {
    // 💡 열(Column) 방향 제어 신호 동기화: c번째 열은 결과가 c클럭 늦게 나오므로 제어 신호도 늦춥니다.
    val skewed_accum_en  = ShiftRegister(io.accum_en, c, false.B)
    val skewed_bias_load = ShiftRegister(io.bias_load, c, false.B)

    // [Phase 1] Accumulator + Bias 
    accumulators(c).io.in_mac_result := mxu(15)(c).io.data.south_out_c
    accumulators(c).io.bias_in       := io.in_bias(c)
    accumulators(c).io.bias_load     := skewed_bias_load // 스큐잉 보정된 신호
    accumulators(c).io.accum_en      := skewed_accum_en  // 스큐잉 보정된 신호
    accumulators(c).io.clear         := io.clear_all

    // [Phase 2] Quantization & Activation LUT
    quant_cores(c).io.in_mac       := accumulators(c).io.out_accum
    quant_cores(c).io.param        := 0x00010800.U 
    quant_cores(c).io.act_en       := io.act_mode_en
    quant_cores(c).io.lut_wr_en    := false.B
    quant_cores(c).io.lut_wr_addr  := 0.U
    quant_cores(c).io.lut_wr_data  := 0.U

    // [Phase 3] Normalization
    norm_lines(c).io.stream_in     := quant_cores(c).io.out_qact
    
    // 💡 파이프라인 딜레이 보상: Accumulator와 QuantCore를 거치며 발생한 2클럭 지연 동기화
    norm_lines(c).io.stream_valid  := ShiftRegister(skewed_accum_en, 2, false.B) 
    
    norm_lines(c).io.mode_sel      := io.norm_mode_sel
    norm_lines(c).io.clr_acc       := io.clear_all

    // 5. 칩 최종 출력 배선
    io.final_post_out(c) := norm_lines(c).io.out_data
    io.final_valid(c)    := norm_lines(c).io.out_valid
  }
}
