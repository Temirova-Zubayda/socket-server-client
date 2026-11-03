# Pinky를 WiFi 네트워크 2개에 연결하기: 초보자 가이드

O'zbekcha: [pinky-wifi-beginner.uz.md](pinky-wifi-beginner.uz.md)

Pinky를 처음 다루는 사람을 위한 가이드입니다. 각 단계를 순서대로 따라 하세요.

## 무엇을 하나요?

Pinky(Raspberry Pi 기반 로봇)에는 WiFi "안테나"가 2개 있습니다.

| 안테나 | Linux 이름 | 연결할 네트워크 | 용도 |
|---|---|---|---|
| 내장 WiFi | `wlan0` | `team2_5G` (팀 라우터) | team2 프로젝트 |
| USB WiFi 어댑터 | `wlx588694f526d6` | `FASTCAMPUS_10F` | FASTCAMPUS 네트워크에서 Pinky 접속 |

완료하면 Pinky는 **IP 주소 2개**를 갖게 되고, 두 네트워크 모두에서 `ping`할 수 있습니다.

```
 노트북 (team2_5G) ────── team2 라우터 ──── wlan0 ─┐
                                                    ├── Pinky
 노트북 (FASTCAMPUS) ──── FASTCAMPUS_10F ── 동글 ──┘
```

## 준비물

- Pinky (전원 켜짐, 배터리 충전됨)
- USB WiFi 어댑터 (Pinky USB 포트에 연결)
- Pinky 접속 방법: 모니터 + 키보드 **또는** 같은 네트워크에 있는 노트북
- Pinky 사용자: `pinky`, 비밀번호는 팀에 문의
- WiFi 비밀번호: `team2_5G`, `FASTCAMPUS_10F` (팀에 문의)

아래 명령어의 `<TEAM2_비밀번호>`, `<FASTCAMPUS_비밀번호>`를 실제 비밀번호로 바꾸세요.

## 기본 개념 (간단히)

- **IP 주소**: 네트워크에서 기기의 "집 주소". 예: `192.168.180.53`
- **인터페이스**: 네트워크에 연결되는 부분(안테나). `wlan0`, `wlx...` 등
- **ping**: "들리니?" 하고 메시지를 보내고 응답을 기다림. 응답이 오면 연결됨
- **SSH**: 다른 컴퓨터에서 Pinky 터미널에 원격 접속
- **sudo**: 관리자 권한으로 실행. 비밀번호를 물으면 Pinky 비밀번호 입력 (입력해도 화면에 안 보이는 것이 정상)

---

## 1단계. Pinky 터미널 접속

**A 방법: 모니터와 키보드.** Pinky에 HDMI 모니터와 USB 키보드를 연결하고 `pinky`로 로그인합니다.

**B 방법: SSH.** 노트북이 Pinky와 같은 네트워크에 있어야 합니다. 노트북 터미널에서:

```bash
ssh pinky@<PINKY_IP>
```

중요: `pinky@`를 꼭 입력하세요. 없으면 노트북 사용자 이름으로 접속을 시도해서 비밀번호가 맞지 않습니다. 처음 접속 시 `yes/no`를 물으면 `yes`를 입력합니다.

터미널에 `pinky@raspi:~$`가 보이면 Pinky 안에 들어온 것입니다.

## 2단계. 인터페이스 확인

```bash
nmcli device
```

결과에서 찾을 것:
- `wlan0` → 내장 WiFi
- `wlx...`로 시작하는 이름 → USB 어댑터. 안 보이면 어댑터를 뺐다가 다시 꽂고 명령어를 다시 실행
- `ap0` → Pinky 자체 핫스팟 (`192.168.4.1`), 건드리지 않습니다

## 3단계. 내장 WiFi(`wlan0`) → `team2_5G`

⚠️ 지금 `wlan0`을 통해 SSH로 접속 중이라면 이 단계 후 SSH가 끊깁니다. 모니터와 키보드로 하는 것이 안전합니다.

**3.1. 네트워크 검색.** 필수입니다. 안 하면 `No network found` 오류가 날 수 있습니다:

```bash
sudo nmcli device wifi rescan ifname wlan0
nmcli device wifi list ifname wlan0 | grep -i team2
```

목록에 `team2_5G`가 보여야 합니다.

**3.2. 연결:**

```bash
sudo nmcli device wifi connect "team2_5G" password "<TEAM2_비밀번호>" ifname wlan0 name team2-router
```

`successfully activated`가 나오면 연결 완료.

**3.3. 기존 FASTCAMPUS 프로필 자동 연결 끄기.** `wlan0`이 전에 FASTCAMPUS에 연결되어 있었다면, 재부팅 시 다시 그쪽으로 가지 않도록:

```bash
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
```

(`unknown connection`이 나오면 그런 프로필이 없는 것이니 괜찮습니다.)

## 4단계. USB 어댑터 → `FASTCAMPUS_10F`

참고: 이 어댑터는 **2.4 GHz** 네트워크만 지원합니다. `FASTCAMPUS_10F`는 사용 가능합니다.

**4.1. 네트워크 검색:**

```bash
sudo nmcli device wifi rescan ifname wlx588694f526d6
nmcli device wifi list ifname wlx588694f526d6 | grep FASTCAMPUS
```

**4.2. 연결:**

```bash
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<FASTCAMPUS_비밀번호>" ifname wlx588694f526d6 name fastcampus-dongle
```

**4.3. 재부팅 시 자동 연결:**

```bash
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection modify team2-router connection.autoconnect yes
```

## 5단계. IP 주소 확인

```bash
ip -br addr
```

예상 결과:

```
wlan0            UP   192.168.180.53/24 ...
wlx588694f526d6  UP   192.168.129.116/17 ...
ap0              UP   192.168.4.1/24
```

`wlan0`과 `wlx...` 모두 IP가 있으면 두 네트워크에 연결된 것입니다. IP를 메모해 두세요.

⚠️ IP는 라우터가 할당하므로 Pinky를 재부팅하면 바뀔 수 있습니다. 매번 이 명령어로 확인하세요.

## 6단계. Pinky 안에서 ping

각 안테나로 인터넷이 되는지 확인:

```bash
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8
```

- `-I wlan0`: 이 안테나를 통해 보내기
- `-c 4`: 4번 보내기
- `8.8.8.8`: Google 서버

`4 received, 0% packet loss`가 나오면 정상.

## 7단계. 노트북에서 Pinky로 ping

노트북이 연결된 WiFi와 **같은 네트워크**에 있는 Pinky IP로 ping합니다.

노트북이 어떤 WiFi에 있는지 확인:

```bash
nmcli -t -f active,ssid dev wifi | grep '^yes'
```

| 노트북 네트워크 | ping할 주소 |
|---|---|
| `team2_5G` | `wlan0` IP, 예: `ping -c 4 192.168.180.53` |
| `FASTCAMPUS_10F` | 동글 IP, 예: `ping -c 4 192.168.129.116` |

`0% packet loss`가 나오면 완료! 🎉

SSH도 같은 주소로: `ssh pinky@192.168.180.53` 또는 `ssh pinky@192.168.129.116`

---

## 문제 해결

| 메시지 / 증상 | 원인 | 해결 |
|---|---|---|
| `No network with SSID ... found` | 검색 안 함, 또는 신호 약함 | `sudo nmcli device wifi rescan ifname <인터페이스>` 후 재시도 |
| `Secrets were required` | WiFi 비밀번호 틀림 | 비밀번호 확인 |
| USB 어댑터에 `team2_5G`가 안 보임 | 어댑터가 2.4 GHz 전용 | `team2_5G`는 내장 WiFi로 연결 (또는 어댑터를 `team2_2_4G`에) |
| `Destination Host Unreachable` (노트북에서) | 노트북과 Pinky가 다른 네트워크, 또는 IP 변경 | 5단계, 7단계 표 확인 |
| SSH가 `zubayda@...'s password`를 물음 | `pinky@` 빠짐 | `ssh pinky@<IP>` |
| `wlx...` 인터페이스 없음 | 어댑터 인식 안 됨 | 다시 꽂기; `lsusb`로 확인 |
| SSH가 갑자기 끊김 | SSH가 쓰던 인터페이스가 다른 네트워크로 이동 | Pinky의 다른 IP 또는 모니터로 접속 |

## 요약 (전체 명령어)

```bash
# Pinky에서
nmcli device
sudo nmcli device wifi rescan ifname wlan0
sudo nmcli device wifi connect "team2_5G" password "<TEAM2_비밀번호>" ifname wlan0 name team2-router
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
sudo nmcli device wifi rescan ifname wlx588694f526d6
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<FASTCAMPUS_비밀번호>" ifname wlx588694f526d6 name fastcampus-dongle
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection modify team2-router connection.autoconnect yes
ip -br addr
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8

# 노트북에서
ping -c 4 <Pinky_IP>
ssh pinky@<Pinky_IP>
```
