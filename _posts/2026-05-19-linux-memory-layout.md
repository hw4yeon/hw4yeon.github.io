---
title: "Linux 메모리 레이아웃"
date: 2026-05-19 09:00:00 +0900
categories: [Study, Dreamhack, System Hacking]
summary: "리눅스 프로세스 메모리를 코드·데이터·BSS·힙·스택 5개 세그먼트로 나눠 정리했습니다."
---

## 리눅스 프로세스의 메모리 구조

### 메모리 레이아웃(Memory Layout)

리눅스에서는 프로세스의 메모리를 크게 5가지 세그먼트(Segment)로 구분

→ 세그먼트(Segment): 프로세스 메모리를 용도별로 나누어 관리하는 영역

- 코드 세그먼드(Code Segment)
    - CPU가 실제로 실행하는 명령어들이 저장되는 공간
    - 실행할 수 있어야 하므로 읽기 권한과 실행 권한이 주어짐
    - 쓰기 권한은 안주어짐 → 해커가 취약점을 이용하여 프로그램의 코드를 수정할 수 있어
    - 어셈블리어에서는 section .text: 를 입력한 뒤 아랫줄에 어셈블리어 코드를 입력하여 컴파일 시 코드 세그먼트에 기계 코드가 자리잡히게 됨
    
    ```c
    section .data
        message db "Hello, World!", 0xA
        message_len equ $ - message
    
    section .text
        global _start
    
    _start:
        mov rax, 1
        mov rdi, 1
        mov rsi, message
        mov rdx, message_len
        syscall
    
        mov rax, 60
        xor rdi, rdi
        syscall
    ```
    
- 데이터 세그먼트
    - 컴파일 시점에 값이 정해진 전역 변수 및 전역 상수들이 위치
    - CPU가 이 세그먼트의 데이터를 읽을 수 있어야 하므로, 읽기 권한 부여
    - 쓰기가 가능한 세그먼트와 쓰기가 불가능한 세그먼트로 분류
        - 쓰기가 가능한 세그먼트: 전역 변수와 같이 프로그램이 실행되면서 값이 변할 수 있는 데이터들이 위치 → Data 세그먼트
        - 쓰기가 불가능한 세그먼트(rodata(read-only data) 세그먼트): 프로그램이 실행되면서 값이 변하면 안되는 데이터들 위치, 전역으로 선언된 상수가 여기에 포함
        - 문자열 자체가 수정 가능한지 여부에 따라 data 또는 rodata 영역에 저장
    - str_ptr은 “readonly” 라는 문자역을 가리키고 있는데, 이 문자열은 상수 문자열로 취급하여 rodata에 위치하며, 이를 가리키는 str_ptr은 전역 변수로서 data에 위치
        
        ```c
        int data_num = 31337;                       // data
        char data_rwstr[] = "writable_data";        // data
        const char data_rostr[] = "readonly_data";  // rodata
        char *str_ptr = "readonly";  // str_ptr은 data, 문자열은 rodata
        
        int main() { ... }
        ```
        
- BSS 세그먼트(BSS Segment, Block Started By Symbol Segment)
    - 컴파일 시점에 값이 정해지지 않은 전역 변수가 위치하는 메모리 영역
    - 개발자가 선언만 하고 초기화하지 않은 전역변수 등이 포함
    - 운영체제가 프로그램이 시작될 때, BSS 영역을 모두 0으로 초기화
    - 읽기 권한 및 쓰기 권한 부여
    - 아래 코드에서 초기화되지 않은 전역 변수인 bss_data가 BSS 세그먼트에 위치
    
    ```c
    int bss_data;
    
    int main() {
      printf("%d\n", bss_data);  // 0
      return 0;
    }
    ```
    
- 스택 세그먼트(Stack Segment)
    - 프로세스의 스택에 위치하는 영역
    - 함수의 매개변수나 지역 변수같은 임시 변수들이 실행 중에 이곳에 저장
    - 읽기 권한 및 쓰기 권한 부여
    - 스택 프레임(Stack Frame): 스택을 구성하는 단위
        - 매개변수, 반환 주소, 지역 변수를 저장
        - 각 함수가 실행을 마쳤을 때 해당 함수가 어느 함수로부터 호출 되었는지에 대한 경로와 함수의 정보를 저장하기 위해 존재함
        - 함수들의 영역을 구분해주는 역할
    - CPU가 자유롭게 값을 읽고 쓸 수 있어야 하므로, 읽기와 쓰기 권한 부여
- 힙 세그먼트(Heap Segment)
    - 힙 데이터가 위치하는 세그먼트
    - 실행 중 크기가 동적으로 변하는 데이터를 저장할 때 사용
    - C언어에서 malloc(), calloc() 등을 오출해서 할당받는 메모리가 이 세그먼트에 위치
    - 읽기와 쓰기 권한 부여

&lt;aside&gt;
💡

각 세그먼트는 역할과 접근 권한이 다르며, 이를 통해 운영체제는 메모리를 효율적이고 안전하게 관리함

&lt;/aside&gt;

#### 전역 변수와 지역 변수

| 구분 | 전역 변수(Global Variable) | 지역 변수(Local Variable) |
| --- | --- | --- |
| 선언 위치 | 함수 외부 | 함수 내부 |
| 사용 범위 | 프로그램 전체 | 선언된 함수 내부 |
| 생성 시점 | 프로그램 시작 시 | 함수 호출 시 |
| 소멸 시점 | 프로그램 종료 시 | 함수 종료 시 |
| 저장 영역 | Data/BSS Segment | Stack Segment |
| 특징 | 여러 함수에서 접근 가능 | 해당 함수에서만 사용 가능 |
| 예시 | int global_num = 10; | int local_num = 5; |

```c
int global_num = 10; // 전역 변수

void func() {
    int local_num = 5; // 지역 변수
}
```
