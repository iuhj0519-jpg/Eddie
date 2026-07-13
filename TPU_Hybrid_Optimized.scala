import chisel3._
import chisel3.util._

// =====================================================================
// [HYBRID TPU] 두 설계의 최고 장점 통합
// =====================================================================
// ✅ TPU_revised: 간단한 파이프라인 + Valid 토큰 동기화
// ✅ MatMul: 온라인 Softmax (Milakov) + 안정적인 수치 처리
// ✅ NEW: 하이브리드 - 빠른 처리 + 정확한 정규화
// =====================================================================

// =====================================================================
// [1] 데이터 흐름 인터페이스 (Valid 신호 포함)
// =====================================================================
class HybridSystolicIO extends Bundle {
  val west_in_a   = Input(UInt(8.W))
  val east_out_a  = Output(UInt(8.W))
  val north_in_c  = Input(UInt(16.W))
  val south_out_c = Output(UInt(16.W))
  val north_valid = Input(Bool())
  val south_valid = Output(Bool())
}

// =====================================================================
// [2] 단일 MAC Unit (TPU_revised 채택)
// =====================================================================
class HybridMacUnit extends Module {
  val io = IO(new Bundle {
    val data      = new HybridSystolicIO()
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
  io.data.south_valid := RegNext(io.data.north_valid, false.B)
}

// =====================================================================
// [3] 누산기 (TPU_revised 채택 - Valid 토큰 자동 생성)
// =====================================================================
class HybridAccumBufferChannel extends Module {
  val io = IO(new Bundle {
    val in_mac_result = Input(UInt(16.W))
    val in_valid      = Input(Bool())
    val bias_in       = Input(UInt(32.W))
    val bias_load     = Input(Bool())
    val accum_en      = Input(Bool())
    val clear         = Input(Bool())
    
    val out_accum     = Output(UInt(32.W))
    val out_valid     = Output(Bool())
  })
  
  val shift_reg = RegInit(VecInit(Seq.fill(16)(0.U(32.W))))
  val valid_shift = RegInit(VecInit(Seq.fill(16)(false.B)))

  val current_sum = shift_reg(0) + io.in_mac_result.zext.asUInt

  when(io.clear) {
    for (i <- 0 until 16) { 
      shift_reg(i) := 0.U 
      valid_shift(i) := false.B
    }
  }.elsewhen(io.bias_load) {
    shift_reg(15) := io.bias_in
    valid_shift(15) := false.B
    for (i <- 0 until 15) { 
      shift_reg(i) := shift_reg(i + 1)
      valid_shift(i) := valid_shift(i + 1)
    }
  }.elsewhen(io.accum_en) {
    shift_reg(15) := current_sum
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
// [4] VPU: 양자화 및 활성화 (TPU_revised 채택)
// =====================================================================
class HybridQuantActCore extends Module {
  val io = IO(new Bundle {
    val in_mac      = Input(UInt(32.W))
    val in_valid    = Input(Bool())
    val param       = Input(UInt(32.W))
    val act_en      = Input(Bool())
    
    val out_qact    = Output(UInt(8.W))
    val out_valid   = Output(Bool())
  })
  
  // Stage 1: 산술 연산 (조합 논리)
  val zp    = io.param(7, 0).asSInt
  val shift = io.param(12, 8).asUInt
  val mult  = io.param(31, 16).zext.asSInt

  val sub_res  = io.in_mac.asSInt.pad(33) - zp.pad(33)
  val mult_res = sub_res * mult
  val shift_res_10b = (mult_res >> (shift - 2.U)).asSInt
  val clamped_idx_10b = Mux(shift_res_10b < 0.S, 0.U(10.W), 
                             Mux(shift_res_10b > 1023.S, 1023.U(10.W), 
                                 shift_res_10b(9, 0).asUInt))

  val stage1_idx   = RegNext(clamped_idx_10b)
  val stage1_lin   = RegNext(clamped_idx_10b(9, 2))
  val stage1_en    = RegNext(io.act_en)
  val stage1_valid = RegNext(io.in_valid, false.B)

  // Stage 2: BRAM Read
  val act_lut_bram = SyncReadMem(1024, UInt(8.W))
  val lut_out = act_lut_bram(stage1_idx)
  
  val stage2_lin   = RegNext(stage1_lin)
  val stage2_en    = RegNext(stage1_en)
  val stage2_valid = RegNext(stage1_valid, false.B)

  io.out_qact  := Mux(stage2_en, lut_out, stage2_lin)
  io.out_valid := stage2_valid
}

// =====================================================================
// [5] VPU: 하이브리드 정규화
// (TPU_revised의 간단한 구조 + MatMul의 온라인 Softmax 안정화)
// =====================================================================
class HybridUniversalNormLine extends Module {
  val io = IO(new Bundle {
    val stream_in      = Input(UInt(8.W))
    val stream_valid   = Input(Bool())
    val window_clear   = Input(Bool())
    val mode_sel       = Input(UInt(2.W))  // 0: RMSNorm, 1: LayerNorm, 2: Softmax
    
    val out_data       = Output(UInt(8.W))
    val out_valid      = Output(Bool())
  })
  
  // ────────────────────────────────────────────────────────────
  // [Phase 1] 통계량 누적 (공통)
  // ────────────────────────────────────────────────────────────
  val count = RegInit(0.U(16.W))
  val sum1  = RegInit(0.U(32.W))  // E[X]
  val sum2  = RegInit(0.U(32.W))  // E[X²] 또는 Softmax ExpSum
  
  // [MatMul의 온라인 Softmax 장점 적용]
  val max_reg  = RegInit(0.U(8.W))  // Softmax 최댓값 추적 ⭐
  val is_new_max = io.stream_in > max_reg
  
  // Softmax 전용: 지수 테이블 (256-Entry, 간단함)
  val exp_lut = Mem(256, UInt(16.W))
  
  when(io.window_clear) {
    count := 0.U
    sum1 := 0.U
    sum2 := 0.U
    max_reg := 0.U
  }.elsewhen(io.stream_valid) {
    count := count + 1.U
    
    // [공통] LayerNorm / RMSNorm 누적
    sum1 := sum1 + io.stream_in.zext.asUInt
    val sq_val = io.stream_in * io.stream_in
    
    // [선택적] Softmax 온라인 처리 (MatMul의 Milakov 알고리즘)
    when(io.mode_sel === 2.U) {
      // Softmax 온라인 누적
      val diff_norm = io.stream_in - max_reg  // x - max (최댓값이 유지될 때)
      val diff_old  = max_reg - io.stream_in  // old_max - new_max (최댓값 변경 시)
      val exp_val   = exp_lut(diff_norm)
      val scale_old = exp_lut(diff_old)
      
      val next_softmax_sum = Mux(is_new_max,
        ((sum2 >> 8) * scale_old) + 1.U,  // 기존 합 보정 + e^0
        sum2 + exp_val                     // 기존 최댓값 유지, 누적
      )
      
      when(is_new_max) { max_reg := io.stream_in }
      sum2 := next_softmax_sum
    }.otherwise {
      // RMSNorm / LayerNorm: 제곱합 누적
      sum2 := sum2 + sq_val
    }
  }

  // ────────────────────────────────────────────────────────────
  // [Phase 2] 정규화 계산 (TPU_revised 기반, 간단함)
  // ────────────────────────────────────────────────────────────
  val count_shift = Mux(count >= 64.U, 6.U,
                    Mux(count >= 32.U, 5.U,
                    Mux(count >= 16.U, 4.U,
                    Mux(count >= 8.U,  3.U,
                    Mux(count >= 4.U,  2.U,
                    Mux(count >= 2.U,  1.U, 0.U))))))

  val mu_wire = sum1 >> count_shift 
  val var_algebraic = (sum2 >> count_shift) - (mu_wire * mu_wire)
  val final_reduction = MuxLookup(io.mode_sel, sum2 >> count_shift)(Seq(
    0.U -> (sum2 >> count_shift),        // RMSNorm: E[X²]
    1.U -> var_algebraic,               // LayerNorm: Var
    2.U -> sum2                          // Softmax: ExpSum (이미 정규화됨)
  ))

  // ────────────────────────────────────────────────────────────
  // [정규화 적용]
  // ────────────────────────────────────────────────────────────
  val lz_count = PriorityEncoder(final_reduction.asBools.reverse)
  val norm_res = Mux(io.mode_sel === 2.U,
    // Softmax: 이미 정규화되었으므로 클램핑만
    io.stream_in.zext.asUInt,
    // RMSNorm / LayerNorm: 스케일링
    (io.stream_in.zext.asUInt << (lz_count(2, 0)))
  )
  
  io.out_data  := RegNext(Mux(norm_res > 255.U, 255.U(8.W), norm_res(7, 0)))
  io.out_valid := RegNext(io.stream_valid, false.B)
}

// =====================================================================
// [6] 16x16 시스톨릭 어레이 (TPU_revised 채택)
// =====================================================================
class HybridSystolicArray extends Module {
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
    
    val out_accum       = Output(Vec(16, UInt(32.W)))
    val out_valid       = Output(Vec(16, Bool()))
  })

  val mxu          = Seq.fill(16, 16)(Module(new HybridMacUnit()))
  val accumulators = Seq.fill(16)(Module(new HybridAccumBufferChannel()))

  // --- [오케스트레이터: Data Skewing 및 Valid 토큰] ---
  val skewed_input = Wire(Vec(16, UInt(8.W)))
  for (r <- 0 until 16) {
    skewed_input(r) := ShiftRegister(io.in_input(r), r, 0.U, io.feed_enable)
  }

  val ctrl_delay_chain = RegInit(VecInit(Seq.fill(16)(false.B)))
  ctrl_delay_chain(0) := io.load_enable
  for (r <- 1 until 16) { ctrl_delay_chain(r) := ctrl_delay_chain(r - 1) }

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
        mxu(r)(0).io.data.west_in_a := skewed_input(r)
        if (r == 0) mxu(0)(c).io.data.north_valid := ShiftRegister(is_last_k, c, false.B)
      } else {
        mxu(r)(c).io.data.west_in_a := mxu(r)(c - 1).io.data.east_out_a
        if (r == 0) mxu(0)(c).io.data.north_valid := 0.U
      }
      
      if (r == 0) mxu(0)(c).io.data.north_in_c := 0.U
      else {
        mxu(r)(c).io.data.north_in_c  := mxu(r - 1)(c).io.data.south_out_c
        mxu(r)(c).io.data.north_valid := mxu(r - 1)(c).io.data.south_valid
      }
    }
  }
  
  for (c <- 1 until 16) {
    mxu(0)(c).io.data.north_valid := ShiftRegister(is_last_k, c, false.B)
  }

  // --- [누산기 배선] ---
  for (c <- 0 until 16) {
    val skewed_accum_en  = ShiftRegister(io.accum_en, c, false.B)
    val skewed_bias_load = ShiftRegister(io.bias_load, c, false.B)

    accumulators(c).io.in_mac_result := mxu(15)(c).io.data.south_out_c
    accumulators(c).io.in_valid      := mxu(15)(c).io.data.south_valid
    accumulators(c).io.bias_in       := io.in_bias(c)
    accumulators(c).io.bias_load     := skewed_bias_load
    accumulators(c).io.accum_en      := skewed_accum_en
    accumulators(c).io.clear         := io.clear_all

    io.out_accum(c) := accumulators(c).io.out_accum
    io.out_valid(c) := accumulators(c).io.out_valid
  }
}

// =====================================================================
// [7] 최종 완성형 탑 모듈 (하이브리드 최적화)
// =====================================================================
class HybridTPU_Top extends Module {
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
    val norm_mode_sel   = Input(UInt(2.W))  // 0: RMSNorm, 1: LayerNorm, 2: Softmax
    
    val final_post_out  = Output(Vec(16, UInt(8.W)))
    val final_valid     = Output(Vec(16, Bool()))
  })

  val systolic = Module(new HybridSystolicArray())
  val quant_cores = Seq.fill(16)(Module(new HybridQuantActCore()))
  val norm_lines  = Seq.fill(16)(Module(new HybridUniversalNormLine()))

  // --- [Systolic Array 배선] ---
  systolic.io.in_input     := io.in_input
  systolic.io.in_weight    := io.in_weight
  systolic.io.in_bias      := io.in_bias
  systolic.io.feed_enable  := io.feed_enable
  systolic.io.load_enable  := io.load_enable
  systolic.io.swap_weights := io.swap_weights
  systolic.io.bias_load    := io.bias_load
  systolic.io.accum_en     := io.accum_en
  systolic.io.clear_all    := io.clear_all

  // --- [VPU 파이프라인 핸드셰이크] ---
  for (c <- 0 until 16) {
    // QuantActCore
    quant_cores(c).io.in_mac       := systolic.io.out_accum(c)
    quant_cores(c).io.in_valid     := systolic.io.out_valid(c)
    quant_cores(c).io.param        := 0x00010200.U
    quant_cores(c).io.act_en       := io.act_mode_en

    // HybridUniversalNormLine (온라인 Softmax 포함)
    norm_lines(c).io.stream_in     := quant_cores(c).io.out_qact
    norm_lines(c).io.stream_valid  := quant_cores(c).io.out_valid
    norm_lines(c).io.window_clear  := io.clear_all
    norm_lines(c).io.mode_sel      := io.norm_mode_sel

    // 최종 출력
    io.final_post_out(c) := norm_lines(c).io.out_data
    io.final_valid(c)    := norm_lines(c).io.out_valid
  }
}
