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

## 매니저 교체 시

Vercel 환경변수의 `ADMIN_PASSWORD`만 바꾸고 재배포하면 됩니다.
GitHub 계정이나 토큰을 공유할 필요가 없습니다.

## 로컬 개발 (선택)

```bash
npm install -g vercel
cd admin-web
vercel dev
```
