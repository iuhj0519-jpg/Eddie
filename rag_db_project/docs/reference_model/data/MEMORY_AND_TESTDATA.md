# Reference Memory and Test Data

- 문서 ID: REF-DATA-001
- 상태: draft-for-review

## Weight 및 bias

파일 이름은 다음 규칙을 따른다.

```text
w_<layer>_<neuron>.mif
b_<layer>_<neuron>.mif
```

| Layer | 입력 수 | neuron 수 | Weight 파일 | Bias 파일 |
|---|---:|---:|---:|---:|
| 1 | 784 | 30 | 30 | 30 |
| 2 | 30 | 20 | 20 | 20 |
| 3 | 20 | 10 | 10 | 10 |
| 합계 | - | 60 | 60 | 60 |

각 neuron은 `Weight_Memory.v`의 `$readmemb(weightFile, mem)`로 weight를 읽고, `neuron.v`에서 `$readmemb(biasFile, biasReg)`로 bias를 읽는다.

## Activation LUT

`sigContent.mif`는 `Sig_ROM.v`가 읽는 sigmoid lookup table이다. 원본 RTL은 파일 이름만 사용하므로 시뮬레이션 working directory에서 해당 파일을 찾을 수 있어야 한다.

## Test data

baseline에는 다음 100개를 사용한다.

```text
test_data_0000.txt ... test_data_0099.txt
```

각 파일은 785개 binary text entry로 구성된다.

- entry 0~783: image pixel 784개
- entry 784: expected class label

`top_sim.v`는 각 파일을 `in_mem[784:0]`에 읽고 784개 입력을 DUT로 전송한 뒤 마지막 entry를 expected label로 사용한다.

## RAG 인덱싱 원칙

- Verilog는 module/symbol 단위로 인덱싱한다.
- MIF와 test vector의 모든 숫자를 embedding하지 않는다.
- MIF/testdata는 파일명, layer/neuron, entry 수, SHA-256 및 원본 경로를 metadata로 관리한다.
- 정확한 수치가 필요할 때 Agent가 원본 파일을 직접 읽는다.
