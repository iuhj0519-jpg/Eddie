import chisel3._
import chisel3.util._


class StallDistributorIO extends Bundle {
  // Input : Stall Generator로부터 취합된 최종 단일 global stall 신호
  val globalStallIn = Input(Bool())

  // Outputs : 각 OCM Controller와 Unit들로 분배되는 pipelined stall signals
  // Upper Cluster Stall Outputs (Adjacent in the upper physical layout)
  val pbStall   = Output(Bool())
  val ubStall   = Output(Bool())
  val wbStall   = Output(Bool())

  // Lower Cluster Stall Outputs (Adjacent in the lower physical layout & Compute Unit)
  val vbStall   = Output(Bool())
  val nbStall   = Output(Bool())
  val dmaWStall = Output(Bool())
  val cuStall   = Output(Bool()) // Compute Unit Stall (TPU/VPU)
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
  io.dmaWStall := lowerStall
  io.cuStall   := lowerStall
}