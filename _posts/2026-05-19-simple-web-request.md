---
title: "simple-web-request"
date: 2026-05-19 10:00:00 +0900
categories: [Study, Wargame, Web]
summary: "GET/POST 방식의 차이를 정리하고 단계별로 플래그를 획득한 워게임 풀이입니다."
---

### 문제 설명

STEP 1~2를 거쳐 FLAG 페이지에 도달하면 플래그가 출력됩니다.

모든 단계를 통과하여 플래그를 획득하세요. 플래그는 flag.txt 파일과 FLAG 변수에 있습니다.

플래그 형식은 DH{...} 입니다.

### GET / POST

- 웹 사이트에서는 사용자가 입력한 데이터를 서버로 전달해야 하는 상황이 자주 발생함
- 이때 데이터를 전달하는 대표적인 방식이 바로 GET 방식과 POST 방식임

#### GET 방식이란?

- 데이터를 URL에 포함하여 서버에 전달하는 방식
- 예를 들어 사용자가 검색창에 apple을 검색했다고 가정했을 때, 브라우저 주소창은 다음과 같이 변함

```plaintext
https://example.com/search?query=apple
```

| 구성 요소 | 의미 |
| --- | --- |
| search | 요청 페이지 |
| query | 파라미터 이름 |
| apple | 전달되는 값 |

#### Query String 이란?

GET 방식에서 URL 뒤에 붙는 데이터

```plaintext
/search?query=apple&page=1
```

여기서 Query String은 ?query=apple&page=1

| 기호 | 역할 |
| --- | --- |
| ? | Query String 시작 |
| & | 여러 데이터 구분 |
| = | 변수와 값 연결 |

#### POST 방식이란?

- 데이터를 URL이 아니라 요청 Body에 담아 서버로 전달하는 방식
- 로그인 요청을 보낸다고 가정했을 때, ID: test / PW: 1234 라는 데이터를 입력함
- 하지만 GET 방식과 달리 주소창에는 비밀번호가 보이지 않음

```plaintext
https://example.com/login
```

- 실제 데이터는 브라우저 내부의 요청 Body에 포함되어 서버로 전달

Flask에서는 GET 요청의 Query String 데이터를 request.args로 가져오고 POST 요청의 Body 데이터를 request.form으로 가져옴

### 문제 풀이

VM 접속을 하면 아래 화면이 보임

![스크린샷 2026-05-18 12.26.03.png](/assets/img/simple-web-request/01.png)

#### STEP 1

![스크린샷 2026-05-18 12.26.55.png](/assets/img/simple-web-request/02.png)

제공해준 python 파일을 확인해 보면 아래 코드가 step 1 코드

```python
@app.route("/step1", methods=["GET", "POST"])
def step1():

    #### 풀이와 관계없는 치팅 방지 코드
    global step1_num
    step1_num = int.from_bytes(os.urandom(16), sys.byteorder)
    ####

    if request.method == "GET":
        prm1 = request.args.get("param", "")
        prm2 = request.args.get("param2", "")
        step1_text = "param : " + prm1 + "\nparam2 : " + prm2 + "\n"
        if prm1 == "getget" and prm2 == "rerequest":
            return redirect(url_for("step2", prev_step_num = step1_num))
        return render_template("step1.html", text = step1_text)
    else: 
        return render_template("step1.html", text = "Not POST")
```

```python
if prm1 == "getget" and prm2 == "rerequest":
```

이 조건문을 확인해보면 첫 번째 값이 "getget", 두 번째 값이 "rerequest" 임을 확인할 수 있음

두 조건을 모두 만족할 경우

```python
return redirect(url_for("step2", prev_step_num = step1_num))
```

이 코드가 실행 됨

redirect()는 사용자를 다른 페이지로 이동시키는 함수이며, 현재 코드에서는 사용자를 step2 페이지로 이동시키고 있음

#### STEP 2

step 2 코드

```python
@app.route("/step2", methods=["GET", "POST"])
def step2():
    if request.method == "GET":

    #### 풀이와 관계없는 치팅 방지 코드
        if request.args.get("prev_step_num"):
            try:
                prev_step_num = request.args.get("prev_step_num")
                if prev_step_num == str(step1_num):
                    global step2_num
                    step2_num = int.from_bytes(os.urandom(16), sys.byteorder)
                    return render_template("step2.html", prev_step_num = step1_num, hidden_num = step2_num)
            except:
                return render_template("step2.html", text="Not yet")
        return render_template("step2.html", text="Not yet")
    ####

    else: 
        return render_template("step2.html", text="Not POST")
```

```python
if request.args.get("prev_step_num"):
```

이 조건문은 사용자가 STEP 1을 정상적으로 통과했는지 확인하는 부분

STEP 1에서 redirect가 발생할 때

```python
prev_step_num = step1_num
```

값이 함께 전달되었음

STEP 2에서는 해당 값이 서버에 step1_num 값과 동일한지 검사

```python
step2_num = int.from_bytes(os.urandom(16), sys.byteorder)
```

이 조건문을 확인해보면 첫 번째 값은 "pooost", 두 번째 값은 "requeeest" 임을 확인할 수 있음

![스크린샷 2026-05-18 12.33.32.png](/assets/img/simple-web-request/03.png)

STEP 3

![스크린샷 2026-05-18 12.34.23.png](/assets/img/simple-web-request/04.png)

값을 입력하면 FLAG 값이 나옴

```plaintext
DH{c46b414ddba26adfa4606c59655bda0a18fbe260606b042b52d865e0160eea0e}
```
