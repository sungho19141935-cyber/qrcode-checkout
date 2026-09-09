# 퇴실 QR 관리자 웹페이지

GitHub 계정/토큰 없이, 비밀번호만으로 QR을 갱신할 수 있는 관리자 페이지입니다.
Vercel 서버리스 함수가 GitHub 토큰을 서버 쪽에만 보관하고, 관리자는 비밀번호로만 인증합니다.
학생 프로그램이 읽는 Gist 구조는 그대로 유지되므로 학생 쪽 설정은 바꿀 필요 없습니다.

## 배포

1. Vercel 대시보드 → **Add New Project** → 이 저장소를 import
2. **Root Directory**를 `admin-web`으로 지정
3. 환경변수(Settings → Environment Variables) 등록:

   | 변수 | 값 | 설명 |
   |---|---|---|
   | `GITHUB_TOKEN` | `ghp_...` | `gist` 권한만 있는 Personal Access Token |
   | `GIST_ID` | `5cd259614734afe93651c086fdcad554` | 갱신할 Gist ID |
   | `GIST_FILENAME` | `bootcamp_qr_config.json` | Gist 안의 파일명 |
   | `GIST_RAW_URL` | `https://gist.githubusercontent.com/사용자/GIST_ID/raw/bootcamp_qr_config.json` | 현재 값 조회용 |
   | `ADMIN_PASSWORD` | (원하는 비밀번호) | 관리자 웹페이지 로그인 비밀번호 |

4. Deploy
5. 배포된 주소(`https://프로젝트명.vercel.app`)를 관리자(매니저)에게 전달

## 페이지에서 비밀번호 변경하기 (선택, 1회 설정 필요)

기본값(`ADMIN_PASSWORD` 환경변수)은 Vercel 대시보드에서만 바꿀 수 있고 재배포도 필요합니다.
**페이지 안에서 바로 비밀번호를 바꾸고 싶다면** 아래 1회 설정을 해두세요. 비밀번호 해시를
학생 프로그램이 읽는 공개 Gist와는 **완전히 분리된 별도의 secret gist**에 저장하므로 안전합니다.

1. https://gist.github.com/ 접속 → **New gist**
2. 파일 이름: `admin_auth.json`, 내용: `{}`
3. **Create secret gist** 클릭 (Create **public** gist 아님! 반드시 secret으로)
4. 생성된 Gist의 URL에서 Gist ID 확인 (예: `https://gist.github.com/내아이디/abcdef...` → `abcdef...` 부분)
5. Vercel 환경변수에 추가:

   | 변수 | 값 |
   |---|---|
   | `AUTH_GIST_ID` | 방금 만든 secret gist의 ID |

   (`GITHUB_TOKEN`은 이미 등록된 걸 그대로 씁니다 — 새로 만들 필요 없음)
6. 재배포 (이 설정을 위한 마지막 재배포입니다 — 이후 비밀번호 변경은 페이지에서 즉시 반영되고 재배포가 필요 없습니다)

설정 후에는 관리자 페이지 하단의 "비밀번호 변경" 카드에서 현재 비밀번호 확인 후 바로 바꿀 수 있습니다.

## 설정 저장/불러오기 (프리셋)

QR/시각/요일/링크 조합을 이름 붙여 저장해두고 나중에 다시 불러올 수 있습니다
(예: "설정1", "특강주"). 별도 설정 없이 바로 사용 가능하며, 저장된 프리셋은
학생 프로그램이 읽는 파일과는 다른 파일(`admin_presets.json`, 같은 gist 안)에
저장되어 학생 쪽 트래픽에는 영향이 없습니다. "불러오기"는 입력칸만 채울 뿐이라,
학생에게 실제로 반영하려면 이어서 "저장" 버튼을 눌러야 합니다.

## 매니저 교체 시

위 1회 설정을 해두었다면, 관리자 페이지에서 새 매니저가 쓸 비밀번호로 바로 바꾸면 됩니다
(재배포 불필요). 설정을 안 했다면 Vercel 환경변수의 `ADMIN_PASSWORD`를 바꾸고 재배포하세요.
어느 경우든 GitHub 계정이나 토큰을 매니저와 공유할 필요는 없습니다.

## 로컬 개발 (선택)

```bash
npm install -g vercel
cd admin-web
vercel dev
```
