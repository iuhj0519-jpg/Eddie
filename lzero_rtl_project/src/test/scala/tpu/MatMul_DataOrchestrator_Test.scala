import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest.simulator.WriteVcdAnnotation

// =========================================================
// [1] 단일 MAC Unit 테스트 — 기존 코드와 동일 (변경 없음)
// =========================================================
class MyMacUnitTest extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "MyMacUnit"

  it should "correctly load weight and compute MAC with 1 clock delay" in {
    test(new MyMacUnit()).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      // 1. Weight 장전: weight_ctrl을 1로 켜고 5를 넣습니다.
      dut.io.weight_ctrl.poke(true.B)
      dut.io.weight_in.poke(5.U)
      dut.clock.step(1)
      dut.io.weight_ctrl.poke(false.B)

      // 2. 연산 테스트: A = 3, C(위에서 내려온 부분합) = 10
      dut.io.data.west_in_a.poke(3.U)
      dut.io.data.north_in_c.poke(10.U)
      dut.clock.step(1)

      // 3. 결과 검증: (3 * 5) + 10 = 25
      dut.io.data.south_out_c.expect(25.U)
      dut.io.data.east_out_a.expect(3.U)
    }
  }
}

// =========================================================
// [2] Data Orchestrator 단독 테스트 (신규)
// =========================================================
// r번째 행에 넣은 임펄스가 정확히 r클럭 뒤에만 출력되는지 검증합니다.
class DataOrchestratorTest extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DataOrchestrator"

  it should "delay row r's input by exactly r clock cycles" in {
    test(new DataOrchestrator(16)).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      // 모든 행에 서로 다른 값(row index + 1)을 1클럭짜리 임펄스로 동시 주입
      for (r <- 0 until 16) dut.io.in_A(r).poke((r + 1).U)

      // 0번 행은 지연이 없으므로(ShiftRegister(_, 0) = 조합 논리) 클럭 전에도 즉시 확인 가능
      dut.io.out_A(0).expect(1.U)
      for (r <- 1 until 16) dut.io.out_A(r).expect(0.U) // 아직 도착 전

      dut.clock.step(1) // edge 1: 모든 행의 "1단계" 레지스터가 임펄스를 동시에 포착
      dut.io.in_A.foreach(_.poke(0.U)) // 임펄스는 1클럭만 유지하고 즉시 종료

      // edge1 직후: row0은 이미 0(조합 경로라 입력 변화가 바로 반영), row1은 1클럭 지연 후 도착
      dut.io.out_A(0).expect(0.U)
      dut.io.out_A(1).expect(2.U)
      for (r <- 2 until 16) dut.io.out_A(r).expect(0.U)

      // 나머지 행들도 각자 정해진 클럭에서만 값이 나타나는지 순차 확인
      for (r <- 2 until 16) {
        dut.clock.step(1)
        for (rr <- 0 until 16) {
          if (rr == r) dut.io.out_A(rr).expect((rr + 1).U)
          else         dut.io.out_A(rr).expect(0.U)
        }
      }
    }
  }
}

// =========================================================
// [3] MyTPU_Complete_Top 통합 테스트 (신규)
// =========================================================
// Orchestrator + MXU + Accumulator가 유기적으로 연결되어
// 실제 행렬-벡터 곱셈 결과를 끝까지 정확히 산출하는지 검증합니다.
//
// 검증 시나리오: O(c) = Σ_r A(r) * W(r,c)
//   - A(r)   = r + 1              (1, 2, 3, ..., 16)
//   - W(r,c) = c + 1  (모든 r에 대해 동일, 열마다 다른 값)
//   - 기대값: O(c) = (c+1) * Σ(1..16) = (c+1) * 136
//
// 핵심 포인트: TB는 더 이상 행마다 수동으로 클럭을 밀어 넣지 않고,
// 모든 행의 입력을 "동시에" 한 번만 인가합니다. Skewing은 전적으로
// DataOrchestrator 하드웨어가 담당합니다.
class MyTPU_Complete_TopTest extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "MyTPU_Complete_Top"

  it should "compute A . W correctly through Orchestrator -> MXU -> Accumulator" in {
    test(new MyTPU_Complete_Top(16, 16)).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      // 1. Accumulator 초기화
      dut.io.accum_clr.poke(true.B)
      dut.clock.step(1)
      dut.io.accum_clr.poke(false.B)
      dut.io.accum_en.poke(true.B) // 이후 계속 활성화 (임펄스 입력이라 중복 누적 걱정 없음)

      // 2. 16x16 가중치 장전: W(r,c) = c+1 (모든 행 동일, 열마다 값이 다름)
      for (r <- 0 until 16) {
        for (c <- 0 until 16) {
          dut.io.in_W(r)(c).poke((c + 1).U)
        }
      }
      dut.io.set_W.poke(true.B)
      dut.clock.step(1)
      dut.io.set_W.poke(false.B)

      // 3. Skewing 되지 않은 "원본" 입력을 모든 행에 동시에 인가
      //    -> 하드웨어(DataOrchestrator)가 알아서 행별로 1클럭씩 지연시킴
      for (r <- 0 until 16) dut.io.in_A(r).poke((r + 1).U)
      dut.clock.step(1)
      for (r <- 0 until 16) dut.io.in_A(r).poke(0.U) // 단발성 임펄스이므로 즉시 종료

      // 4. 전체 레이턴시(최대 32사이클 = Orchestrator 지연 15 + 열 전파 15 + 레지스터 1~2단)
      //    + 여유분을 두고 클럭을 흘려보냄
      dut.clock.step(40)

      // 5. 결과 검증: 모든 열(column)에 대해 (c+1) * 136 인지 확인
      val expectedSum = (1 to 16).sum // = 136
      for (c <- 0 until 16) {
        dut.io.out_MAC(c).expect(((c + 1) * expectedSum).U)
      }

      println("MyTPU_Complete_Top End-to-End Verification Passed!")
    }
  }
}
