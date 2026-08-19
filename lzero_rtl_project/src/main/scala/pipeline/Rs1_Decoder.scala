import chisel3._
import chisel3.util._

// NpuRs1Decoder는 rs1에 들어 있는 “현재 NPU 상태”를 읽는 모듈이 아니라, CPU가 요청한 “이번 작업의 설정값”을 분리하는 모듈
// 분리된 설정값을 저장하고 TPU·VPU·DMA에 전달하여 실제 동작시키는 것은 상위 Control Unit의 역할

// Decoding 신호를 담을 signal ports (몇 Bit 단위인지를 정의) -> Bundle 자체에는 동작성X
class NpuRs1Control extends Bundle {
  val fusionEn = Bool()

  // rs1[62:58] (= lut_write) is interpreted as {act, exp, scale, sin, cos}
  val actLutWrite   = Bool() // 4
  val expLutWrite   = Bool() // 3
  val scaleLutWrite = Bool() // 2
  val sinLutWrite   = Bool() // 1
  val cosLutWrite   = Bool() // 0

  // rs1[57:51] (=hw_enables) is interperted as {mxuEn, aluMode, actEn, normMode, ropeEn}
  val mxuEn    = Bool()
  val aluMode  = UInt(2.W) // 2-bit
  val actEn    = Bool()
  val normMode = UInt(2.W) // 2-bit
  val ropeEn   = Bool()

  // transposeEnRd[0] = activation transpose
  // transposeEnRd[1] = weight transpose
  val transposeEnRd = UInt(2.W)
  val transposeEnWr = Bool()

  val tileStridedRd = Bool()
  val tileStridedWr = Bool()

  // MXU : 행렬곱 / VPU1 : ALU, Quantization, Activation / VPU2 : Normalization, RoPE

  // 0: MXU, 1: VPU1, 2: VPU2, 3: reserved (정의되지 않은 예약값)
  val inputPoint = UInt(2.W)

  // 0: VPU2, 1: VPU1, 2/3: reserved (정의되지 않은 예약값)
  val outputPoint = UInt(2.W)

  // Raw 4-bit fields from rs1. A raw value of 0 means all 16 lanes are valid.
  val validRowCountRaw = UInt(4.W)
  val validColCountRaw = UInt(4.W)

  // Interpreted values in the range 1..16.
  val validRows = UInt(5.W)
  val validCols = UInt(5.W)

  val sizeEmbed = Bool()

  // Output sizes in 16-element tile units.
  val outRowTiles   = UInt(11.W)
  val outInterTiles = UInt(11.W)
  val outColTiles   = UInt(11.W)
}

// rs1은 값 자체를 parsing 해석, rs2는 그 값이 가리키는 메모리를 DMA로 읽어야 함

class NpuRs1Decoder extends Module {
  val io = IO(new Bundle {
    val rs1      = Input(UInt(64.W)) // CPU와 RoCC가 이미 읽어서 전달하는 64-bit 입력 정보 -> Bit-Packing
    val cmdValid = Input(Bool()) // 조합 논리 모듈 (현재 rs1이 실제 명령으로 전달된 값인지를 알려줌)

    val ctrl         = Output(new NpuRs1Control) // rs1 입력 신호에 대한 출력 신호

    // CPU가 RISC-V 명령어를 이미 RoCC 커스텀 명령으로 인식해서 NPU에 전달한 뒤, 그 명령의 rs1 내부에 예약된 값이 들어 있는지를 검사
    val decodedValid = Output(Bool()) // 정의된 값
    val illegal      = Output(Bool()) // 정의되지 않은 값 (ex : aluMode에서 11 또는 normMode에서 11)
  })


  // 명세서에 맞게 bit 단위로 쪼갠 하드웨어 Control Flag (ISA 명세서 참고)
  // "io.ctr1.~" 형식으로 실제 비트 연결 수행

  // fusion_en [63] (1-bit)
  io.ctrl.fusionEn := io.rs1(63)
  
  // lut_write [62:58] (5-bit)
  io.ctrl.actLutWrite   := io.rs1(62)
  io.ctrl.expLutWrite   := io.rs1(61)
  io.ctrl.scaleLutWrite := io.rs1(60)
  io.ctrl.sinLutWrite   := io.rs1(59)
  io.ctrl.cosLutWrite   := io.rs1(58)

  // hw_enables [57:51] (7-bit)
  io.ctrl.mxuEn    := io.rs1(57)
  io.ctrl.aluMode  := io.rs1(56, 55) // 2-bit (00 : bypass / 01 : add / 10 : mul / 11 : reserved (정의되지 않은 예약값)) -> 실제 연산 선택은 후속 VPU1/ALU에서 수행
  io.ctrl.actEn    := io.rs1(54)
  io.ctrl.normMode := io.rs1(53, 52) // 2-bit (00 : bypass / 01 : RMSNorm / 10 : LayerNorm / 11 : reserved (정의되지 않은 예약값)) -> 실제 연산 선택은 후속 VPU1/ALU에서 수행
  io.ctrl.ropeEn   := io.rs1(51)

  io.ctrl.transposeEnRd := io.rs1(50, 49) // transpose_en_rd (2-bit)
  io.ctrl.transposeEnWr := io.rs1(48) // transpose_en_wr (1-bit)
  io.ctrl.tileStridedRd := io.rs1(47) // tile_strided_rd (1-bit)
  io.ctrl.tileStridedWr := io.rs1(46) // tile_strided_wr (1-bit)

  io.ctrl.inputPoint  := io.rs1(45, 44) // input_point (00 : MXU / 01 : VPU1 / 10 : VPU2)
  io.ctrl.outputPoint := io.rs1(43, 42) // output_point (00 : VPU2 / 01 : VPU1)

  io.ctrl.validRowCountRaw := io.rs1(41, 38) // valid_row_count_raw (4-bit)
  io.ctrl.validColCountRaw := io.rs1(37, 34) // valid_col_count_raw (4-bit)

  io.ctrl.validRows := Mux(
    io.ctrl.validRowCountRaw === 0.U,
    16.U(5.W),
    Cat(0.U(1.W), io.ctrl.validRowCountRaw) // 4b'0000을 5b'10000으로 만들어 1~16의 숫자로 반환 
  )
  io.ctrl.validCols := Mux(
    io.ctrl.validColCountRaw === 0.U,
    16.U(5.W),
    Cat(0.U(1.W), io.ctrl.validColCountRaw) // 4b'0000을 5b'10000으로 만들어 1~16의 숫자로 반환 
  )

  io.ctrl.sizeEmbed := io.rs1(33) // size_embeded (1-bit) // 행렬 차원 M, K, N을 어디에서 가져올지 선택하는 플래그

  io.ctrl.outRowTiles   := io.rs1(32, 22) // out_rowNum (11-bit)
  io.ctrl.outInterTiles := io.rs1(21, 11) // out_intermNum (11-bit)
  io.ctrl.outColTiles   := io.rs1(10, 0) // out _colNum (11-bit)

  // 예약값이 포함되었는지 판별
  val aluModeReserved     = io.ctrl.aluMode === 3.U
  val normModeReserved    = io.ctrl.normMode === 3.U
  val inputPointReserved  = io.ctrl.inputPoint === 3.U
  val outputPointReserved = io.ctrl.outputPoint >= 2.U
  
  val hasIllegalEncoding =
    aluModeReserved || normModeReserved ||
      inputPointReserved || outputPointReserved // rs1 내부에 예약값(=필드에 정의되지 않은 값)이 있는지를 나타냄

  io.illegal      := io.cmdValid && hasIllegalEncoding // 잘못된 명령인 경우 (실제 명령이 들어왔지만 그 내용에 예약값이 있을 때 1)
  io.decodedValid := io.cmdValid && !hasIllegalEncoding // 정상 명령인 경우 (실제 명령이 들어왔고 그 내용도 정상일 때 1)
}