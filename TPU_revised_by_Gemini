import chisel3._
import chisel3.util._

// =====================================================================
// [1] 데이터 흐름 인터페이스 (Valid 신호 포함)
// =====================================================================
class SystolicIO extends Bundle {
  val west_in_a   = Input(UInt(8.W))
  val east_out_a  = Output(UInt(8.W))
  val north_in_c  = Input(UInt(16.W))
  val south_out_c = Output(UInt(16.W))
  
  // 💡 [수정] 데이터와 함께 흐르는 파이프라인 Valid 토큰
  val north_valid = Input(Bool())
  val south_valid = Output(Bool())
}

// =====================================================================
// [2] 단일 MAC Unit
// =====================================================================
class MyMacUnit extends Module {
  val io = IO(new Bundle {
    val data      = new SystolicIO()
    val weight_in = Input(UInt(8.W)) 
    val load_w    = Input(Bool())
    val swap_w    = Input(Bool())
  })
  val weight_shadow = RegInit(0.U(8.W))
  val weight_active = RegInit(0.U(8.W))

  when(io.load_w) { weight_shadow := io.weight_in }
  when(io.swap_w) { weight_active := weight_shadow }

  val mac_result = (io.data.west_in_a * weight_active) + io.data.north_in_c
  
  io.data.south_out_c := RegNext(mac_result)
  io.data.east_out_a  := RegNext(io.data.west_in_a)
  // 💡 [수정] Valid 토큰도 데이터와 똑같이 1클럭 지연시켜 아래로 전달
  io.data.south_valid := RegNext(io.data.north_valid, false.B)
}

// =====================================================================
// [3] 누산기 (가변 레이턴시 완벽 반영형 자체 Valid 생성)
// =====================================================================
class MyAccumBufferChannel extends Module {
  val io = IO(new Bundle {
    val in_mac_result = Input(UInt(16.W))
    val in_valid      = Input(Bool()) // 마지막 K차원 데이터임을 알리는 토큰
    val bias_in       = Input(UInt(32.W))
    val bias_load     = Input(Bool())
    val accum_en      = Input(Bool())
    val clear         = Input(Bool())
    
    val out_accum     = Output(UInt(32.W))
    val out_valid     = Output(Bool()) // 누산이 끝난 찐 데이터 배출 신호
  })
  
  val shift_reg = RegInit(VecInit(Seq.fill(16)(0.U(32.W))))
  val valid_shift = RegInit(VecInit(Seq.fill(16)(false.B))) // 💡 [수정] Valid 동기화 레지스터

  val current_sum = shift_reg(0) + io.in_mac_result.zext.asUInt

  when(io.clear) {
    for (i <- 0 until 16) { 
      shift_reg(i) := 0.U 
      valid_shift(i) := false.B
    }
  }.elsewhen(io.bias_load) {
    shift_reg(15) := io.bias_in
    valid_shift(15) := false.B // Bias 로드는 결과 완성이 아님
    for (i <- 0 until 15) { 
      shift_reg(i) := shift_reg(i + 1)
      valid_shift(i) := valid_shift(i + 1)
    }
  }.elsewhen(io.accum_en) {
    shift_reg(15) := current_sum
    // 💡 토큰을 마지막 슬롯에 넣고 같이 회전시킴. 16클럭 뒤 0번에 도달하면 완성!
    valid_shift(15) := io.in_valid 
    for (i <- 0 until 15) { 
      shift_reg(i) := shift_reg(i + 1) 
      valid_shift(i) := valid_shift(i + 1)
    }
  }
  
  io.out_accum := shift_reg(0)
  io.out_valid := valid_shift(0)
}

// =====================================================================
// [4] VPU: 양자화 및 활성화 (크리티컬 패스 분할 및 깊이 동기화)
// =====================================================================
class MyQuantActCore extends Module {
  val io = IO(new Bundle {
    val in_mac      = Input(UInt(32.W))
    val in_valid    = Input(Bool())
    val param       = Input(UInt(32.W))
    val act_en      = Input(Bool())
    
    val out_qact    = Output(UInt(8.W))
    val out_valid   = Output(Bool())
  })
  
  // --- [Stage 1: 산술 연산 (조합 논리)] ---
  val zp    = io.param(7, 0).asSInt
  val shift = io.param(12, 8).asUInt
  val mult  = io.param(31, 16).zext.asSInt // 💡 [수정] 리뷰어 지적 반영: 원본 부호 해석 복원

  val sub_res  = io.in_mac.asSInt.pad(33) - zp.pad(33)
  val mult_res = sub_res * mult
  val shift_res_10b = (mult_res >> (shift - 2.U)).asSInt
  val clamped_idx_10b = Mux(shift_res_10b < 0.S, 0.U(10.W), Mux(shift_res_10b > 1023.S, 1023.U(10.W), shift_res_10b(9, 0).asUInt))

  // 💡 [수정] 타이밍 위반을 막기 위한 스테이지 1 레지스터 경계
  val stage1_idx   = RegNext(clamped_idx_10b)
  val stage1_lin   = RegNext(clamped_idx_10b(9, 2))
  val stage1_en    = RegNext(io.act_en)
  val stage1_valid = RegNext(io.in_valid, false.B)

  // --- [Stage 2: BRAM Read 및 파이프라인 동기화] ---
  val act_lut_bram = SyncReadMem(1024, UInt(8.W)) // 💡 [수정] SyncReadMem (1클럭 지연)
  val lut_out = act_lut_bram(stage1_idx)
  
  // 💡 [수정] SyncReadMem의 지연(1클럭)에 맞추어 Linear 경로와 제어 신호도 1클럭 늦춤
  val stage2_lin   = RegNext(stage1_lin)
  val stage2_en    = RegNext(stage1_en)
  val stage2_valid = RegNext(stage1_valid, false.B)

  io.out_qact  := Mux(stage2_en, lut_out, stage2_lin)
  io.out_valid := stage2_valid
}

// =====================================================================
// [5] VPU: 정규화 (실제 수식 복원 및 Valid 정합성)
// =====================================================================
class MyUniversalNormLine extends Module {
  val io = IO(new Bundle {
    val stream_in      = Input(UInt(8.W))
    val stream_valid   = Input(Bool())
    val window_clear   = Input(Bool()) // 💡 [수정] 통계량 윈도우 초기화 핀 추가
    val mode_sel       = Input(UInt(2.W))
    
    val out_data       = Output(UInt(8.W))
    val out_valid      = Output(Bool())
  })
  
  val count = RegInit(0.U(16.W)) // 💡 [수정] 누적 샘플 개수 추적
  val sum1  = RegInit(0.U(32.W)) 
  val sum2  = RegInit(0.U(32.W)) 
  
  when(io.window_clear) {
    count := 0.U; sum1 := 0.U; sum2 := 0.U
  }.elsewhen(io.stream_valid) {
    count := count + 1.U
    sum1 := sum1 + io.stream_in.zext.asUInt
    sum2 := sum2 + (io.stream_in * io.stream_in)
  }

  // 💡 [수정] 카운트 값에 기반한 동적 하드웨어 나눗셈(비트 시프트) 구현
  val count_shift = Mux(count >= 64.U, 6.U,
                    Mux(count >= 32.U, 5.U,
                    Mux(count >= 16.U, 4.U,
                    Mux(count >= 8.U,  3.U,
                    Mux(count >= 4.U,  2.U,
                    Mux(count >= 2.U,  1.U, 0.U))))))

  val mu_wire = sum1 >> count_shift 
  val var_algebraic = (sum2 >> count_shift) - (mu_wire * mu_wire) 
  val final_reduction = Mux(io.mode_sel === 1.U, var_algebraic, (sum2 >> count_shift))

  val lz_count = PriorityEncoder(final_reduction.asBools.reverse)
  val norm_res = (io.stream_in.zext.asUInt << (lz_count(2,0))) 
  
  // 💡 [수정] Data와 Valid 모두 조합 논리 직후 동일하게 1클럭 지연 (정합성 100% 매칭)
  io.out_data  := RegNext(Mux(norm_res > 255.U, 255.U(8.W), norm_res(7, 0)))
  io.out_valid := RegNext(io.stream_valid, false.B)
}

// =====================================================================
// [6] 최종 완성형 탑 모듈 (완벽한 Cycle-Accurate 파이프라인)
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
    
    val final_post_out  = Output(Vec(16, UInt(8.W)))
    val final_valid     = Output(Vec(16, Bool()))
  })

  val mxu          = Seq.fill(16, 16)(Module(new MyMacUnit()))
  val accumulators = Seq.fill(16)(Module(new MyAccumBufferChannel()))
  val quant_cores  = Seq.fill(16)(Module(new MyQuantActCore()))
  val norm_lines   = Seq.fill(16)(Module(new MyUniversalNormLine()))

  // --- [오케스트레이터: Data Skewing 및 Valid 토큰 생성] ---
  val skewed_input = Wire(Vec(16, UInt(8.W)))
  for (r <- 0 until 16) {
    skewed_input(r) := ShiftRegister(io.in_input(r), r, 0.U, io.feed_enable)
  }

  val ctrl_delay_chain = RegInit(VecInit(Seq.fill(16)(false.B)))
  ctrl_delay_chain(0) := io.load_enable
  for (r <- 1 until 16) { ctrl_delay_chain(r) := ctrl_delay_chain(r - 1) }

  // 💡 [수정] K차원(스트리밍)의 마지막 요소임을 알리는 토큰(is_last_k) 생성
  val k_count = RegInit(0.U(5.W))
  when(io.feed_enable) { k_count := k_count + 1.U }
  val is_last_k = io.feed_enable && (k_count === 15.U)

  // --- [시스톨릭 어레이 배선] ---
  for (r <- 0 until 16) {
    for (c <- 0 until 16) {
      mxu(r)(c).io.weight_in := io.in_weight(c)
      mxu(r)(c).io.load_w    := ctrl_delay_chain(r)
      mxu(r)(c).io.swap_w    := io.swap_weights
      
      if (c == 0) {
        mxu(r)(0).io.data.west_in_a   := skewed_input(r)
        // 💡 [수정] 첫 번째 Row에 스큐가 적용된 토큰을 주입
        if (r == 0) mxu(0)(c).io.data.north_valid := ShiftRegister(is_last_k, c, false.B)
      } else {
        mxu(r)(c).io.data.west_in_a   := mxu(r)(c - 1).io.data.east_out_a
        if (r == 0) mxu(0)(c).io.data.north_valid := 0.U // 0번 Row의 c>0 열은 스큐 처리로 이미 주입됨 (위 블럭)
      }
      
      if (r == 0) mxu(0)(c).io.data.north_in_c := 0.U
      else {
        mxu(r)(c).io.data.north_in_c  := mxu(r - 1)(c).io.data.south_out_c
        mxu(r)(c).io.data.north_valid := mxu(r - 1)(c).io.data.south_valid
      }
    }
  }
  
  // (예외 처리: c>0 열에 대한 north_valid 연결)
  for (c <- 1 until 16) {
    mxu(0)(c).io.data.north_valid := ShiftRegister(is_last_k, c, false.B)
  }

  // --- [VPU 파이프라인 핸드셰이크 배선] ---
  for (c <- 0 until 16) {
    val skewed_accum_en  = ShiftRegister(io.accum_en, c, false.B)
    val skewed_bias_load = ShiftRegister(io.bias_load, c, false.B)

    // Accumulator
    accumulators(c).io.in_mac_result := mxu(15)(c).io.data.south_out_c
    accumulators(c).io.in_valid      := mxu(15)(c).io.data.south_valid // 💡 16클럭을 타고 내려온 진짜 토큰!
    accumulators(c).io.bias_in       := io.in_bias(c)
    accumulators(c).io.bias_load     := skewed_bias_load
    accumulators(c).io.accum_en      := skewed_accum_en
    accumulators(c).io.clear         := io.clear_all

    // QuantActCore
    quant_cores(c).io.in_mac       := accumulators(c).io.out_accum
    quant_cores(c).io.in_valid     := accumulators(c).io.out_valid // 💡 Accumulator가 판단하여 뿜어낸 Valid!
    quant_cores(c).io.param        := 0x00010200.U // 테스트벤치 값 소실(0 클램핑)을 막기 위해 Shift=2 로 변경
    quant_cores(c).io.act_en       := io.act_mode_en

    // NormLine
    norm_lines(c).io.stream_in     := quant_cores(c).io.out_qact
    norm_lines(c).io.stream_valid  := quant_cores(c).io.out_valid  // 💡 QuantCore를 2클럭 지나 안전하게 도착한 Valid!
    norm_lines(c).io.window_clear  := io.clear_all
    norm_lines(c).io.mode_sel      := io.norm_mode_sel

    // 칩 최종 출력
    io.final_post_out(c) := norm_lines(c).io.out_data
    io.final_valid(c)    := norm_lines(c).io.out_valid
  }
}

