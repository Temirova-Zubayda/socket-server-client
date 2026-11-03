# Pinky WiFi tarmoq sozlamalari: bajarilgan ishlar (2026-10-19)

Koreyscha versiyasi: [wifi-two-networks.ko.md](wifi-two-networks.ko.md)

## Maqsad

- Pinky'da (Raspberry Pi) ikkita WiFi interfeysdan foydalanish
  - Ichki WiFi (`wlan0`) → jamoa router'i `team2_5G`
  - USB WiFi dongle (`wlx588694f526d6`) → `FASTCAMPUS_10F`
- Noutbukdan (jamoa router'iga ulangan) `ping` bilan Pinky'ga ulanishni tekshirish

## 1. Interfeyslarni aniqlash

```bash
nmcli device
nmcli connection show --active
```

Natija:
- `wlan0` (ichki WiFi): `FASTCAMPUS_10F` ga ulangan edi
- `wlx588694f526d6` (USB dongle): ulanmagan
- `ap0`: Pinky hotspoti (`192.168.4.1`)

## 2. USB dongle → FASTCAMPUS_10F

```bash
sudo nmcli device wifi connect "FASTCAMPUS_10F" password "<parol>" ifname wlx588694f526d6 name fastcampus-dongle
ip -br addr
ping -I wlan0 -c 4 8.8.8.8
ping -I wlx588694f526d6 -c 4 8.8.8.8
```

Natija: Pinky'da 2 ta IP paydo bo'ldi
- `wlan0`: `192.168.129.105`
- `wlx588694f526d6`: `192.168.129.116`
- Ikkala interfeys orqali ham internetga ping o'tdi (0% packet loss)

## 3. Muammo: noutbukdan Pinky'ga ping o'tmadi

```bash
ping 192.168.129.105    # noutbukda
# Destination Host Unreachable
```

Sabab: noutbuk jamoa router'ida (`team2_5G`) edi, Pinky'ning ikkala interfeysi esa `FASTCAMPUS_10F` da. Ular boshqa-boshqa tarmoqda bo'lgani uchun bir-birini topa olmadi.

## 4. Dongle'ni jamoa router'iga ulashga urinish

```bash
sudo nmcli connection down fastcampus-dongle
sudo nmcli connection modify fastcampus-dongle connection.autoconnect no
sudo nmcli device wifi rescan ifname wlx588694f526d6
nmcli device wifi list ifname wlx588694f526d6 | grep team2
```

Natija: dongle faqat `team2_2_4G` (2.4 GHz) ni ko'rdi, `team2_5G` ni ko'rmadi. Demak, bu dongle faqat 2.4 GHz'da ishlaydi.

## 5. Ichki WiFi (wlan0) → team2_5G

```bash
sudo nmcli connection modify FASTCAMPUS_10F connection.autoconnect no
sudo nmcli device wifi rescan ifname wlan0          # avval rescan qilinmagani uchun "No network found" xatosi chiqqan edi
nmcli device wifi list ifname wlan0 | grep -i team2
sudo nmcli device wifi connect "team2_5G" password "<parol>" ifname wlan0 name team2-router
ip -br addr show wlan0
```

Natija: `wlan0` = `192.168.180.53/24` (noutbuk `192.168.180.51` bilan bitta tarmoqda)

## 6. Noutbukdan Pinky'ga ping

```bash
ping -c 4 192.168.180.53
```

Natija: `4 received, 0% packet loss`, o'rtacha ~9 ms → muvaffaqiyatli

Endi SSH: `ssh pinky@192.168.180.53`

## Hozirgi holat

| Interfeys | Tarmoq | IP |
|---|---|---|
| `wlan0` (ichki) | `team2_5G` | `192.168.180.53` |
| `wlx588694f526d6` (dongle) | ulanmagan | - |
| `ap0` (hotspot) | - | `192.168.4.1` |

## O'rganganlarimiz

- `ping -I <interfeys>` bilan aniq bir interfeys orqali ping qilish mumkin
- Boshqa-boshqa WiFi tarmog'idagi qurilmalar bir-biriga ping qila olmaydi
- Ba'zi USB donglelar faqat 2.4 GHz'ni qo'llaydi
- `nmcli` bilan ulanishdan oldin `rescan` qilish kerak, aks holda tarmoq ko'rinmasligi mumkin
- IP'ni router (DHCP) beradi, Pinky qayta yoqilganda o'zgarishi mumkin. Shuning uchun `ip -br addr` bilan tekshirib turing

## (Ixtiyoriy) Dongle'ni yana FASTCAMPUS_10F ga ulash

```bash
sudo nmcli connection modify fastcampus-dongle connection.autoconnect yes
sudo nmcli connection up fastcampus-dongle
ip -br addr
```
