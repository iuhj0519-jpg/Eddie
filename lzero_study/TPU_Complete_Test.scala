package tpu_complete // 💡 핵심: 기존 코드와 이름이 겹치지 않게 격리하는 마법의 명령어

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest.simulator.WriteVcdAnnotation

class MyTPU_Complete_Top_Test extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "MyTPU_Complete_Top"

  it should "execute full pipeline from Orchestration to Normalization autonomously" in {
    test(new MyTPU_Complete_Top()).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      
      // ================================================================
      // [Phase 0] 모든 핀 0으로 초기화
      // ================================================================
      for (i <- 0 until 16) {
        dut.io.in_input(i).poke(0.U)
        dut.io.in_weight(i).poke(0.U)
        dut.io.in_bias(i).poke(0.U)
      }
      dut.io.feed_enable.poke(false.B)
      dut.io.load_enable.poke(false.B)
      dut.io.swap_weights.poke(false.B)
      dut.io.bias_load.poke(false.B)
      dut.io.accum_en.poke(false.B)
      dut.io.act_mode_en.poke(false.B) // 비선형 활성화 끄기 (선형 양자화 테스트)
      dut.io.norm_mode_sel.poke(0.U)   // RMSNorm 모드
      
      // 칩 전체 초기화
      dut.io.clear_all.poke(true.B)
      dut.clock.step(2)
      dut.io.clear_all.poke(false.B)

      println("[Info] Phase 0: Reset Complete")

      // ================================================================
      // [Phase 1] 가중치(Weight) 장전 (DataOrchUnit이 자동으로 Skewing 해줌)
      // ================================================================
      dut.io.load_enable.poke(true.B)
      for (r <- 0 until 16) { // 16클럭 동안 16개 행을 순차적으로 장전
        for (c <- 0 until 16) {
          // 관찰하기 쉽게 모든 가중치를 '2'로 통일하여 장전
          dut.io.in_weight(c).poke(2.U)
        }
        dut.clock.step(1)
      }
      dut.io.load_enable.poke(false.B)
      
      // Shadow Buffer -> Active Buffer로 교체 (이제 연산 준비 완료!)
      dut.io.swap_weights.poke(true.B)
      dut.clock.step(1)
      dut.io.swap_weights.poke(false.B)

      println("[Info] Phase 1: Weight Loading & Swap Complete")

      // ================================================================
      // [Phase 2] Bias 셋업 및 데이터 주입 시작 (수동 Skewing 불필요!)
      // ================================================================
      // 누산기에 깔아둘 편향(Bias) 값으로 '100'을 줍니다.
      for (c <- 0 until 16) dut.io.in_bias(c).poke(100.U)
      
      // 데이터 스트리밍 시작 신호와 누산기/Bias 켜기 신호를 동시에 줍니다.
      // (Top Module 내부의 ShiftRegister들이 알아서 대각선 타이밍으로 쪼개줍니다)
      dut.io.feed_enable.poke(true.B)
      dut.io.accum_en.poke(true.B)
      dut.io.bias_load.poke(true.B) 
      
      // 단 1클럭만 Bias Load 신호를 주고 바로 끕니다. (첫 바닥에만 깔리면 되니까)
      for (r <- 0 until 16) dut.io.in_input(r).poke(3.U) // 모든 입력 A를 '3'으로 통일
      dut.clock.step(1)
      dut.io.bias_load.poke(false.B)

      // 나머지 15클럭 동안 계속 입력 데이터 '3'을 밀어 넣습니다.
      for (clk <- 1 until 16) {
        for (r <- 0 until 16) dut.io.in_input(r).poke(3.U)
        dut.clock.step(1)
      }
      
      // 데이터 주입 완료 (입력 핀 닫기)
      dut.io.feed_enable.poke(false.B)
      for (r <- 0 until 16) dut.io.in_input(r).poke(0.U)

      println("[Info] Phase 2: Input Streaming Complete. Waiting for Pipeline Flush...")

      // ================================================================
      // [Phase 3] 파이프라인 플러싱 (Pipeline Flush)
      // ================================================================
      // 16x16 어레이를 관통하고, 누산기를 거쳐, 양자화 -> 정규화까지 빠져나오려면
      // 물리적으로 최소 30~40 클럭의 고정 레이턴시(Latency)가 필요합니다.
      // 이 시간 동안 컨베이어 벨트가 계속 돌 수 있도록 클럭만 발생시킵니다.
      dut.clock.step(45)

      println("[Success] Full Pipeline Simulation Complete. Please check the .vcd file!")
    }
  }
}
