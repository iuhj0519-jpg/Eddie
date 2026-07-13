import chisel3._
import chisel3.util._

// =========================================================
// [1] 데이터 흐름을 묶어주는 인터페이스 정의 (Bundle)
// =========================================================
class SystolicIO extends Bundle {
  val west_in_a   = Input(UInt(8.W))   // 왼쪽에서 들어오는 Activation
  val east_out_a  = Output(UInt(8.W))  // 오른쪽으로 나가는 Activation
  val north_in_c  = Input(UInt(16.W))  // 위에서 내려오는 Partial Sum
  val south_out_c = Output(UInt(16.W)) // 아래로 내려보내는 Partial Sum
}


// =========================================================
// [2] 단일 MAC Unit (Processing Element) 모듈
// =========================================================
class MyMacUnit extends Module {
  val io = IO(new Bundle {
    val data        = new SystolicIO()
    val weight_ctrl = Input(Bool())    // 가중치 장전 신호 (set_W)
    val weight_in   = Input(UInt(8.W)) // 외부에서 들어오는 가중치 값
  })

  // 제어 신호(weight_ctrl)가 1일 때만 가중치 레지스터 업데이트
  val weight = RegEnable(io.weight_in, 0.U(8.W), io.weight_ctrl)

  // MAC 연산: (A * W) + C
  val mac_result = (io.data.west_in_a * weight) + io.data.north_in_c
  
  // 연산 결과와 Activation 값을 다음 클럭에 전달 (레지스터 통과)
  io.data.south_out_c := RegNext(mac_result)
  io.data.east_out_a  := RegNext(io.data.west_in_a)
}


// =========================================================
// [3] 32-bit 정적 누산기 (Stationary Accumulator) 모듈
// =========================================================
class Accumulator16 extends Module {
  val io = IO(new Bundle {
    val in_mac_results = Input(Vec(16, UInt(16.W))) // MXU 바닥에서 떨어지는 16-bit 값들
    val accum_en       = Input(Bool())              // 누산 활성화 신호
    val clear          = Input(Bool())              // 누산기 초기화 신호
    val out_accum      = Output(Vec(16, UInt(32.W)))// 최종 32-bit 출력
  })

  // 32-bit 크기의 레지스터 16개 생성 (0으로 초기화)
  val accum_regs = RegInit(VecInit(Seq.fill(16)(0.U(32.W))))

  for (i <- 0 until 16) {
    when(io.clear) {
      accum_regs(i) := 0.U
    } .elsewhen(io.accum_en) {
      accum_regs(i) := accum_regs(i) + io.in_mac_results(i) // 값 누적
    }
    
    io.out_accum(i) := accum_regs(i)
  }
}


// =========================================================
// [4] 최종 16x16 MXU + Accumulator 통합 모듈
// =========================================================
class MyMXU_with_Accumulator extends Module {
  val io = IO(new Bundle {
    val in_A      = Input(Vec(16, UInt(8.W)))
    val in_W      = Input(Vec(16, Vec(16, UInt(8.W))))
    val set_W     = Input(Bool())
    
    // 누산기 전용 제어 핀 추가
    val accum_en  = Input(Bool())
    val accum_clr = Input(Bool())
    
    // 최종 출력은 오버플로우 방지를 위해 32-bit로 출력
    val out_MAC   = Output(Vec(16, UInt(32.W)))
  })

  // 1. 16x16 MAC 배열 및 Accumulator 생성
  val macs = Seq.fill(16, 16)(Module(new MyMacUnit()))
  val accumulator = Module(new Accumulator16())

  // 2. MAC 배열 내부 배선 연결
  for (r <- 0 until 16) {
    for (c <- 0 until 16) {
      // 가중치 핀 연결
      macs(r)(c).io.weight_in   := io.in_W(r)(c)
      macs(r)(c).io.weight_ctrl := io.set_W

      // 가로 방향 연결 (Activation A)
      if (c == 0) macs(r)(0).io.data.west_in_a := io.in_A(r)
      else        macs(r)(c).io.data.west_in_a := macs(r)(c-1).io.data.east_out_a

      // 세로 방향 연결 (Partial Sum C)
      if (r == 0) macs(0)(c).io.data.north_in_c := 0.U
      else        macs(r)(c).io.data.north_in_c := macs(r-1)(c).io.data.south_out_c
    }
  }

  // 3. MXU의 맨 아랫줄(15번 Row) 출력을 Accumulator로 연결
  accumulator.io.accum_en := io.accum_en
  accumulator.io.clear    := io.accum_clr

  for (c <- 0 until 16) {
    accumulator.io.in_mac_results(c) := macs(15)(c).io.data.south_out_c
    io.out_MAC(c) := accumulator.io.out_accum(c)
  }
}