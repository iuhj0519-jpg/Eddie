import chisel3._
import chisel3.util._

// MatMul 연산 + Input Matrix Skewing

// =========================================================
// [1] 데이터 흐름을 묶어주는 인터페이스 정의 (Bundle) — 기존과 동일
// =========================================================
class SystolicIO extends Bundle {
  val west_in_a   = Input(UInt(8.W))   // 왼쪽에서 들어오는 Activation
  val east_out_a  = Output(UInt(8.W))  // 오른쪽으로 나가는 Activation
  val north_in_c  = Input(UInt(16.W))  // 위에서 내려오는 Partial Sum
  val south_out_c = Output(UInt(16.W)) // 아래로 내려보내는 Partial Sum
}

// =========================================================
// [2] 단일 MAC Unit (Processing Element) 모듈 — 기존과 동일
// =========================================================
class MyMacUnit extends Module {
  val io = IO(new Bundle {
    val data        = new SystolicIO()
    val weight_ctrl = Input(Bool())     // 가중치 장전 신호 (set_W)
    val weight_in   = Input(UInt(8.W))  // 외부에서 들어오는 가중치 값
  })

  // 제어 신호(weight_ctrl)가 1일 때만 가중치 레지스터 업데이트 (Weight Stationary)
  val weight = RegEnable(io.weight_in, 0.U(8.W), io.weight_ctrl)

  // MAC 연산 : (A * W) + C — 상위 PE에서 내려온 부분합에 이번 PE의 곱을 더함
  // 주의: south_out_c가 16-bit이므로, A/W 값이 커지면 16개 행을 누적하는 동안
  // 배열 내부에서 오버플로우가 날 수 있음 (기존 코드에서 이어받은 제약사항)
  val mac_result = (io.data.west_in_a * weight) + io.data.north_in_c

  // 결과와 Activation을 다음 클럭에 전달 (레지스터 통과 → 시스톨릭 전파의 핵심)
  io.data.south_out_c := RegNext(mac_result)
  io.data.east_out_a  := RegNext(io.data.west_in_a)
}

// =========================================================
// [3] Data Orchestrate Unit — 입력 Skewing 전담 모듈 (신규)
// =========================================================
// 기존에는 TB에서 수동으로 1클럭씩 밀어 넣던 것을, 이제는 하드웨어가 직접 수행
// r번째 행(Row)의 Activation을 r클럭만큼 지연시켜, MXU에 진입하는 시점에 Skewed Wavefront가 생성
class DataOrchestrator(rows: Int = 16) extends Module {
  val io = IO(new Bundle {
    val in_A  = Input(Vec(rows, UInt(8.W)))  // 외부에서 들어오는 원본(Skew 되지 않은) 입력
    val out_A = Output(Vec(rows, UInt(8.W))) // MXU로 나가는 Skewed 입력
  })

  for (r <- 0 until rows) {
    // 0번 행은 지연 없음(조합 논리), r번 행은 r클럭 지연 레지스터 체인
    io.out_A(r) := ShiftRegister(io.in_A(r), r)
  }
}

// =========================================================
// [4] MXU — 16 x 16 MAC 시스톨릭 배열 (Weight Stationary)
// =========================================================
// Accumulator를 분리하여, MXU는 순수하게 "행렬 곱 배열" 역할만 담당
class MyMXU(rows: Int = 16, cols: Int = 16) extends Module {
  val io = IO(new Bundle {
    val in_A    = Input(Vec(rows, UInt(8.W)))             // 이미 Skew된 Activation (Orchestrator 출력)
    val in_W    = Input(Vec(rows, Vec(cols, UInt(8.W))))  // 16x16 가중치
    val set_W   = Input(Bool())                            // 가중치 장전 신호
    val out_MAC = Output(Vec(cols, UInt(16.W)))            // 맨 아랫줄(15번 Row)의 raw 16-bit 부분합
  })

  // 16 x 16 MAC 배열 생성 — 모든 PE가 개별 모듈로 명시적으로 드러남
  val macs = Seq.fill(rows, cols)(Module(new MyMacUnit()))

  for (r <- 0 until rows) {
    for (c <- 0 until cols) {
      // 가중치 핀 연결
      macs(r)(c).io.weight_in   := io.in_W(r)(c)
      macs(r)(c).io.weight_ctrl := io.set_W

      // 가로 방향 연결 (Activation A) — 왼쪽 끝은 외부(Orchestrator) 입력
      if (c == 0) macs(r)(0).io.data.west_in_a := io.in_A(r)
      else        macs(r)(c).io.data.west_in_a := macs(r)(c - 1).io.data.east_out_a

      // 세로 방향 연결 (Partial Sum C) — 맨 윗줄은 0에서 시작
      if (r == 0) macs(0)(c).io.data.north_in_c := 0.U
      else        macs(r)(c).io.data.north_in_c := macs(r - 1)(c).io.data.south_out_c
    }
  }

  // 맨 아랫줄(Row 15) 출력을 그대로 내보냄 (Accumulator 연결은 Top에서 담당)
  for (c <- 0 until cols) {
    io.out_MAC(c) := macs(rows - 1)(c).io.data.south_out_c
  }
}

// =========================================================
// [5] 32-bit 정적 누산기 (Stationary Accumulator) 모듈 — 기존과 동일
// =========================================================
class Accumulator16(cols: Int = 16) extends Module {
  val io = IO(new Bundle {
    val in_mac_results = Input(Vec(cols, UInt(16.W))) // MXU 바닥에서 떨어지는 16-bit 값들
    val accum_en       = Input(Bool())                 // 누산 활성화 신호
    val clear          = Input(Bool())                 // 누산기 초기화 신호
    val out_accum      = Output(Vec(cols, UInt(32.W))) // 최종 32-bit 출력
  })

  val accum_regs = RegInit(VecInit(Seq.fill(cols)(0.U(32.W))))

  for (i <- 0 until cols) {
    when(io.clear) {
      accum_regs(i) := 0.U
    }.elsewhen(io.accum_en) {
      accum_regs(i) := accum_regs(i) + io.in_mac_results(i) // 값 누적
    }
    io.out_accum(i) := accum_regs(i)
  }
}

// =========================================================
// [6] Top-level 모듈 — Orchestrator + MXU + Accumulator 유기적 연결
// =========================================================
// 3개 모듈을 각각 독립적으로 생성해 계층 구조상 모든 모듈이 명시적으로 드러남
// 배선(연결)만 Top에서 담당
class MyTPU_Complete_Top(rows: Int = 16, cols: Int = 16) extends Module {
  val io = IO(new Bundle {
    val in_A      = Input(Vec(rows, UInt(8.W)))           // Skew 되지 않은 원본 입력 (하드웨어가 알아서 skew)
    val in_W      = Input(Vec(rows, Vec(cols, UInt(8.W))))
    val set_W     = Input(Bool())
    val accum_en  = Input(Bool())
    val accum_clr = Input(Bool())
    val out_MAC   = Output(Vec(cols, UInt(32.W)))
  })

  val orchestrator = Module(new DataOrchestrator(rows))
  val mxu          = Module(new MyMXU(rows, cols))
  val accumulator  = Module(new Accumulator16(cols))

  // Orchestrator : 원본 입력을 받아 하드웨어에서 Skewing 수행
  orchestrator.io.in_A := io.in_A

  // MXU : Orchestrator가 만든 Skewed 입력을 받아 행렬 곱 수행
  mxu.io.in_A  := orchestrator.io.out_A
  mxu.io.in_W  := io.in_W
  mxu.io.set_W := io.set_W

  // Accumulator : MXU의 raw 16-bit 출력을 받아 32-bit로 누적
  accumulator.io.in_mac_results := mxu.io.out_MAC
  accumulator.io.accum_en       := io.accum_en
  accumulator.io.clear          := io.accum_clr

  io.out_MAC := accumulator.io.out_accum
}
