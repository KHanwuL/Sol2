# Sol2 - Discord Bot for PS

## Introduction

Sol2는 discord.py와 [solved.ac 비공식 api](https://solvedac.github.io/unofficial-documentation/#/)를 이용하여 PS(Problem Solving)을 돕는 Discord Bot입니다.

Sol2는 BOJ의 [그룹 기능](https://www.acmicpc.net/group/list)을 강화하고, 라이벌 기능을 추가하여 다른 사람들과 같이 공부하고, 동기 부여를 얻도록 돕습니다.

**AI 활용**  
해당 프로젝트는 Nano Banana를 활용하여 로고를 제작하였습니다.

## Getting Started

### 사전 요구 사항

* Python 3.10 이상
* Git

### 프로젝트 클론

```shell
git clone https://github.com/KHanwuL/Sol2.git
```

### 라이브러리 설치

```shell
pip install -r requirements.txt
```

### 환경 변수 설정 (.env)

프로젝트 루트 경로에 .env 파일을 생성하고, 디스코드 봇 토큰을 입력해야 합니다.  

1. .env 파일 생성
2. 아래 내용 붙여넣기 및 토큰 입력

```env
DISCORD_TOKEN=봇_토큰_입력
```

봇 토큰 얻는 법:

1. [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications) 접속
2. New Application 생성 후 Bot 탭 이동
3. Reset Token을 눌러 토큰 복사
4. Privileged Gateway Intents 항목에서 **Server Members Intent**와 **Message Content Intent**를 반드시 켜야 합니다.

### 봇 실행

```shell
python bot.py
```

터미널에 [봇이름]으로 로그인했습니다! 메시지가 뜨면 성공입니다

## 기능 및 명령어

### 기본 명령어

**/등록** (solvedac_id):  
Sol2 db에 solved.ac 사이트의 아이디를 등록합니다.  
디스코드 계정 당 하나의 아이디만 등록이 가능하며 중복 등록은 불가능합니다.

**/문제** (problem_id):  
problem_id 백준 문제에 대한 정보를 출력힙니다. (임시로 제목만 출력합니다.)

**/푼문제** (solvedac_id):  
solvedac_id가 푼 문제 중 top 50 문제를 모두 출력합니다.

### 서버장 전용 명령어

#### /그룹장

* **/그룹장** 부여 (member):  
그룹장 역할을 부여합니다.
* **/그룹장** 제거 (member):  
그룹장 역할을 제거합니다.

Sol2_Manager 역할을 부여하거나 제거합니다.
Sol2_Manager 역할은 그룹을 만들고, 문제집을 만들 수 있는 권한을 줍니다.

### 그룹장 전용 명령어

#### /그룹

* **/그룹** 생성 (group_name):  
group_name 그룹을 생성하고, 전용 채팅 채널을 생성합니다.
* **/그룹** 삭제 (group_name):  
group_name 그룹을 삭제합니다. 전용 채팅 채널은 삭제되지 않으므로 직접 삭제해야합니다.

#### /문제집

* **/문제집** 생성 (set_name):  
set_name 문제집을 생성합니다.
* **/문제집** 삭제 (set_name):  
set_name 문제집을 삭제합니다.

#### /문제집문제

* **/문제집문제** 추가 (set_name) (problem_id):  
set_name 문제집에 problem_id 백준 문제를 추가합니다.  
  * [히스토그램에서 가장 큰 직사각형](https://www.acmicpc.net/problem/6549)를 test 문제집에 추가할 경우: /문제집문제 추가 test 6549
* **/문제집문제** 삭제 (set_name) (problem_id):  
set_name 문제집의 problem_id 문제를 삭제합니다.

### 그룹 채널 전용 명령어

그룹 전용 채널에서 사용할 수 있는 명령어입니다. 해당 그룹에 대한 정보를 출력합니다.

#### /그룹정보

* **/그룹정보**:  
그룹에 대한 정보(그룹장, 그룹원 등)을 출력합니다.

#### /그룹원

* **/그룹원** 참가:  
해당 그룹에 참여합니다. 해당 그룹 채팅 채널에 참가하였다는 메세지를 보냅니다.
* **/그룹원** 탈퇴:  
해당 그룹을 탈퇴합니다.
* **/그룹원** 정보:  
해당 그룹의 그룹원들의 solved.ac 프로필 링크를 출력합니다.

#### /문제집보기

* **/문제집보기**:  
그룹장이 생성한 모든 문제집을 출력합니다.

#### /문제집문제보기

* **/문제집문제보기 (set_name)**:  
set_name 문제집의 문제들을 출력합니다.

### 라이벌 관련 명령어

#### /라이벌

* **/라이벌** 추가 (rival_id):  
라이벌 목록에 rival_id를 추가합니다.
* **/라이벌** 삭제 (rival_id):  
라이벌 목록에 rival_id를 삭제합니다.

#### /라이벌목록

* **/라이벌목록**:  
자신이 설정한 라이벌 목록을 출력합니다.
* **/역라이벌목록**:  
자신을 라이벌로 설정한 사람들을 목록으로 출력합니다.

#### /라이벌도전장

* **/라이벌도전장** (rival_id):  
라이벌이 푼 문제 중 자신이 풀지 못한 문제를 최대 50문제 출력합니다.

## 기타

![백준스터디](/img/BaekJoon_Algorithm_Study.JPG)
해당 프로젝트는 동아리 알고리즘 스터디 중 [백준 사이트](https://www.acmicpc.net/)에서 제공하는 그룹 기능이 부족하다 느껴져 제작하게 되었습니다.

![솔브닥라이벌](/img/Solvedac_Rival.JPG)
solved.ac의 라이벌 기능 또한 목록 보기 외엔 기능이 없기 때문에 beatmania iidx의 [라이벌 도전장](https://p.eagate.573.jp/game/2dx/33/howto/epass/rival.html) 기능을 추가하였습니다.

처음에는 Beautiful Soup을 활용하여 백준 사이트를 스크래핑하려고 하였으나 백준은 [웹 스크래핑을 금지하고 있어](https://help.acmicpc.net/rule) solved.ac의 비공식 api를 활용하였습니다.

하지만 solved.ac api의 기능이 한정적이였기 때문에 원했던 기능들을 구현하지 못해 많이 아쉽습니다
