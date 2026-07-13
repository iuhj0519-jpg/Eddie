import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import chiseltest.simulator.WriteVcdAnnotation // VCD 파형 추출을 위한 어노테이션 추가
import scala.util.Random

// =========================================================
// [1] 단일 MAC Unit 테스트 (VCD 추출 포함)
// =========================================================
class MyMacUnitTest extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "MyMacUnit"

  it should "correctly load weight and compute MAC with 1 clock delay" in {
    // WriteVcdAnnotation을 추가하여 파형(.vcd) 파일 생성
    test(new MyMacUnit()).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      
      // 1. Weight 장전: weight_ctrl을 1로 켜고 5를 넣습니다.
      dut.io.weight_ctrl.poke(true.B)
      dut.io.weight_in.poke(5.U)
      dut.clock.step(1) // 클럭이 뛰면서 내부에 5가 저장됨
      dut.io.weight_ctrl.poke(false.B) // 장전 완료 후 신호 끄기

      // 2. 연산 테스트: A = 3, C(위에서 내려온 부분합) = 10
      dut.io.data.west_in_a.poke(3.U)
      dut.io.data.north_in_c.poke(10.U)
      
      // 우리 코드는 RegNext를 통과하므로 결과가 나오려면 1클럭이 필요합니다.
      dut.clock.step(1) 

      // 3. 결과 검증: (3 * 5) + 10 = 25
      dut.io.data.south_out_c.expect(25.U)
      dut.io.data.east_out_a.expect(3.U) // A 데이터도 오른쪽으로 잘 넘어갔는지 확인
    }
  }
}

// =========================================================
// [2] 16x16 MXU + Accumulator 통합 테스트 (VCD 추출 포함)
// =========================================================
class MyMXU_with_AccumulatorTest extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "MyMXU_with_Accumulator"

  it should "load 256 weights, multiply skewed inputs, and accumulate to 32-bit" in {
    test(new MyMXU_with_Accumulator()).withAnnotations(Seq(WriteVcdAnnotation)) { dut =>
      
      // 랜덤 데이터 생성
      val sw_weight = Array.tabulate(16, 16) { (_, _) => Random.nextInt(5) }
      
      // 1. Accumulator 초기화
      dut.io.accum_clr.poke(true.B)
      dut.clock.step(1)
      dut.io.accum_clr.poke(false.B)
      
      // Accumulator 활성화 (테스트 내내 켜둠)
      dut.io.accum_en.poke(true.B)

      // 2. 16x16 Weight 장전
      for (r <- 0 until 16) {
        for (c <- 0 until 16) {
          dut.io.in_W(r)(c).poke(sw_weight(r)(c).U)
        }
      }
      dut.io.set_W.poke(true.B)
      dut.clock.step(1)
      dut.io.set_W.poke(false.B)

      // 3. 간단한 대각선(Skewed) 입력 테스트 (3 Cycle만 진행하여 파형 확인 목적)
      // 실제로는 16번의 레이턴시와 31번의 사이클이 필요하지만, VCD 파형으로 
      // 데이터가 흘러들어가는 모습을 직관적으로 보기 위해 간단한 값만 주입합니다.
      
      // Cycle 0: [Row 0]에만 데이터 주입
      dut.io.in_A(0).poke(2.U)
      for (i <- 1 until 16) dut.io.in_A(i).poke(0.U)
      dut.clock.step(1)
      
      // Cycle 1: [Row 0]과 [Row 1]에 데이터 주입
      dut.io.in_A(0).poke(3.U)
      dut.io.in_A(1).poke(4.U) // 1클럭 지연된(Skewed) 형태
      dut.clock.step(1)

      // Cycle 2~18: 클럭을 쭉 밀어주어 데이터가 바닥(Accumulator)까지 도달하도록 함
      for (i <- 0 until 16) dut.io.in_A(i).poke(0.U) // 입력 중단
      dut.clock.step(20)

      println("MXU Simulation Complete. Please check the generated .vcd waveform file!")
    }
  }
}