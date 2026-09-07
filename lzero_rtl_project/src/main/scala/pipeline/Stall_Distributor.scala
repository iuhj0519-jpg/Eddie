import chisel3._
import chisel3.util._


/*
  * [Distribution Tree Structure Diagram]
  *
  *                          [Impending Inputs]
  *   (ubImpending, wbImpending, pbImpending, nbImpending, vbImpending, initStall)
  *                                     │
  *                                     ▼ (Combinational OR)
  *                               ┌───────┐
  *                               │  OR   │
  *                               └───┬───┘
  *                                   │ (rawStall)
  *                                   ▼
  *                           ┌──────────────┐
  *                           │ rootStallReg │  <--- [Cycle 1 Latency] (Central Root Register)
  *                           └──────┬───────┘
  *                                  ├───┐
  *                                  ▼   ▼ (Routing Branch)
  *                 ┌────────────────┘   └────────────────┐
  *                 ▼                                     ▼
  *         ┌───────────────┐                     ┌───────────────┐
  *         │ upperStallReg │                     │ lowerStallReg │  <--- [Cycle 2 Latency] (Regional Branch Registers)
  *         └───────┬───────┘                     └───────┬───────┘
  *         ┌───────┼───────┐                     ┌───────┼───────┬───────┬───────┐
  *      [ pb ]  [ ub ]  [ wb ]                [ vb ]  [ nb ]  [tpu ]  [vpu1]  [vpu2]
  *      Stall   Stall   Stall                 Stall   Stall   Stall   Stall   Stall
  *
  *      └───── Upper Cluster ─────┘           └───────── Lower Cluster & CU ─────────┘
*/

// [Compute Unit Stall 분배 세분화]
// Compute Unit의 Stall 신호를 단일화하지 않고, 주요 연산 파이프라인(TPU, VPU Stage 1, VPU Stage 2)으로 세분화하여 분배
// Transposer 같이 물리적 규모가 작고 파이프라인 제어에 미치는 영향이 적은 서브 모듈은 Stall 라우팅 대상에서 제외

// [dma_w_stall 신호 제외]
// dma_w_stall은 단순히 Write FIFO가 가득 찼음을 알리는 데이터 흐름 제어(Flow control) 상태 신호
// 따라서 연산 유닛들의 Backpressure를 제어하기 위한 본 Global Stall 분배망의 Output 노드에서는 제외

class StallDistributorIO extends Bundle {
  // Input : Stall Generator로부터 취합된 최종 단일 global stall 신호
  val globalStallIn = Input(Bool())

  // Outputs : 각 OCM Controller와 Unit들로 분배되는 pipelined stall signals
  // Upper Cluster Stall Outputs (Adjacent in the upper physical layout)
  val pbStall   = Output(Bool()) // parameter buffer
  val ubStall   = Output(Bool()) // unified buffer
  val wbStall   = Output(Bool()) // weight buffer

  // Lower Cluster Stall Outputs (Adjacent in the lower physical layout & Compute Unit)
  val vbStall   = Output(Bool())
  val nbStall   = Output(Bool()) // normalizer buffer

  // Compute Unit Stalls (세분화)
  val tpuStall  = Output(Bool()) // TPU Stage
  val vpu1Stall = Output(Bool()) // VPU Stage 1
  val vpu2Stall = Output(Bool()) // VPU Stage 2
}


class StallDistributor extends Module {
  // IO 선언 시 위에서 정의한 StallDistributorIO Bundle을 인스턴스화하여 사용
  val io = IO(new StallDistributorIO)


  // StallDistributor는 외부 StallGenerator가 취합해 준 단일 Global Stall 입력 신호를 사용
  val rawStall = io.globalStallIn

  // ==========================================
  // Stage 1 : Root Register (1st Latency Cycle)
  // ==========================================
  // 글로벌 단일 신호에 대해 중앙에서 1차로 클락 타이밍을 정렬(Latching)
  val rootStallReg = RegNext(rawStall, false.B)

  // ==========================================
  // Stage 2 : Regional Registers (2nd Latency Cycle)
  // ==========================================
  // 물리적 배치에 따른 신호의 Fan-Out 완화를 위해 상/하단 클러스터별로 분기 레지스터를 배치
  val upperStall = RegNext(rootStallReg, false.B) // Upper OCM (PB, UB, WB) 전용 분기 레지스터
  val lowerStall = RegNext(rootStallReg, false.B) // Lower OCM 및 Compute Unit (VB, NB, DMA, CU) 전용 분기 레지스터

  // ==========================================
  // Stage 3 : Output Assignment
  // ==========================================
  // Upper Cluster에 해당하는 컨트롤러들에 분배 (2-Cycle Latency 적용)
  io.pbStall := upperStall
  io.ubStall := upperStall
  io.wbStall := upperStall

  // Lower Cluster 및 Compute Unit에 해당하는 컨트롤러들에 분배 (2-Cycle Latency 적용)
  io.vbStall   := lowerStall
  io.nbStall   := lowerStall
  io.tpuStall  := lowerStall
  io.vpu1Stall := lowerStall
  io.vpu2Stall := lowerStall
}
