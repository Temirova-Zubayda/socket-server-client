# Pinky WiFi 네트워크 설정 작업 정리 (2026-10-19)

## 목표

- Pinky(Raspberry Pi)에 WiFi 인터페이스 2개를 사용
  - 내장 WiFi(`wlan0`) → 팀 라우터 `team2_5G`
  - USB WiFi 동글(`wlx588694f526d6`) → `FASTCAMPUS_10F`
- 노트북(팀 라우터에 연결됨)에서 `ping`으로 Pinky 연결 확인

## 1. 인터페이스 확인

```bash
nmcli device
nmcli connection show --active
```

결과:
- `wlan0` (내장 WiFi): `FASTCAMPUS_10F`에 연결되어 있었음
- `wlx588694f526d6` (USB 동글): 연결 안 됨
- `ap0`: Pinky 핫스팟 (`192.168.4.1`)

## 2. USB 동글 → FASTCAMPUS_10F 연결

```bash
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<비밀번호>" ifname wlx588694f526d6 name fastcampus-dongle
ip -br addr
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8
```

결과: Pinky에 IP 2개
- `wlan0`: `192.168.129.105`
- `wlx588694f526d6`: `192.168.129.116`
- 두 인터페이스 모두 인터넷 ping 성공 (0% packet loss)

## 3. 문제: 노트북에서 Pinky로 ping 실패

```bash
ping 192.168.129.105    # 노트북에서
# Destination Host Unreachable
```

원인: 노트북은 팀 라우터(`team2_5G`)에 연결되어 있고, Pinky의 두 인터페이스는 모두 `FASTCAMPUS_10F`에 있었음. 서로 다른 네트워크라 접근 불가.

## 4. 동글을 팀 라우터에 연결 시도

```bash
sudo nmcli connection down fastcampus-dongle
sudo nmcli connection modify fastcampus-dongle connection.autoconnect no
sudo nmcli device wifi rescan ifname wlx588694f526d6
nmcli device wifi list ifname wlx588694f526d6 | grep team2
```

결과: 동글은 `team2_2_4G`(2.4 GHz)만 보이고 `team2_5G`는 안 보임 → 이 동글은 2.4 GHz 전용.

## 5. 내장 WiFi(wlan0) → team2_5G 연결

```bash
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
sudo nmcli device wifi rescan ifname wlan0          # 처음에는 rescan 없이 "No network found" 오류
nmcli device wifi list ifname wlan0 | grep -i team2
sudo nmcli device wifi connect "team2_5G" password "<비밀번호>" ifname wlan0 name team2-router
ip -br addr show wlan0
```

결과: `wlan0` = `192.168.180.53/24` (노트북 `192.168.180.51`과 같은 네트워크)

## 6. 노트북 → Pinky ping 확인

```bash
ping -c 4 192.168.180.53
```

결과: `4 received, 0% packet loss`, 평균 약 9 ms → 성공

이제 SSH 접속: `ssh pinky@192.168.180.53`

## 현재 상태

| 인터페이스 | 네트워크 | IP |
|---|---|---|
| `wlan0` (내장) | `team2_5G` | `192.168.180.53` |
| `wlx588694f526d6` (동글) | 연결 안 됨 | - |
| `ap0` (핫스팟) | - | `192.168.4.1` |

## 배운 점

- `ping -I <인터페이스>`로 특정 인터페이스를 통해 ping 가능
- 다른 WiFi 네트워크에 있는 기기끼리는 ping이 안 됨
- 일부 USB 동글은 2.4 GHz만 지원
- `nmcli` 연결 전에 `rescan`을 먼저 해야 네트워크가 보일 수 있음
- IP는 라우터(DHCP)가 주므로 재부팅 후 바뀔 수 있음 → `ip -br addr`로 확인

## (선택) 동글을 다시 FASTCAMPUS_10F에 연결

```bash
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection up fastcampus-dongle
ip -br addr
```
