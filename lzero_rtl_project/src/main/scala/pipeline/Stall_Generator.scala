import chisel3._

/*
OCM Controller와 DMA Write Controller에서 전달되는 impending 신호를 모아
Compute Unit 전체에 배포할 global stall 신호를 생성
*/

/*
각 impending 입력은 실제 underflow 또는 overflow가 발생한 뒤가 아니라,
해당 위험이 발생하기 전에 충분한 시간 여유를 두고 올라와야 함
*/

/*
극도로 단순한 논리 게이트와 타이밍 격리(Isolation)용 플립플롭만으로 구성되어 
칩의 크리티컬 패스(Critical Path)를 보호
*/

/* 
단 하나의 모듈이라도 "8클럭 이내 정지"를 외치면, raw_stall이 즉시 High가 되는데,
그 전에 주변 OCM Controller가 8클록 이내 위험을 판단해 impending을 출력
*/

class StallGenerator extends Module {
  val io = IO(new Bundle {
    // Unified Buffer의 input 데이터 고갈 임박 신호
    val ub_impending = Input(Bool())

    // Weight Buffer의 weight 데이터 고갈 임박 신호
    val wb_impending = Input(Bool())

    // Parameter Buffer의 parameter 데이터 고갈 임박 신호
    val pb_impending = Input(Bool())

    // Normalizer Buffer의 데이터 고갈 또는 방출 정체 임박 신호
    val nb_impending = Input(Bool())

    // DMA Write FIFO의 overflow 임박 신호
    val dma_w_impending = Input(Bool())

    // 추가
    val initStall = Input(Bool())

    // Compute Unit의 연산 파이프라인을 일시 정지시키는 신호
    val global_stall = Output(Bool())
  })

  // 어느 한 Controller에서라도 위험을 예고하면 stall 요청을 생성
  val raw_stall =
    io.ub_impending ||
      io.wb_impending ||
      io.pb_impending ||
      io.nb_impending ||
      io.dma_w_impending ||
      io.initStall

  /*
  global_stall 신호는 MXU(Systolic Array), VPU, Accumulator Local Timer 등
  칩 전역에 위치한 수만 개의 FF으로 뿌려져야 하는 초대형 Fan-Out 신호
  */

  // 생략 (굳이 지연시키지 않아도 된다는 지침)
  /*
  // 조합 논리(raw_stall)를 그대로 칩 전역에 뿌리면 Timing Violation(셋업 타임 에러) 발생
  // 긴 조합 경로와 큰 fan-out을 피하도록 OR 결과를 D-FF에 한 번 저장해서 해결
  // global_stall은 raw_stall보다 1-cycle 늦게 변하며 reset 시 0으로 초기화

  io.global_stall := RegNext(raw_stall, false.B)
  */
}