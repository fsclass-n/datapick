import { Link } from 'react-router-dom'

const UPDATED = '2026-11-17'

const TERMS = [
  ['제1조 (목적)', '이 약관은 datapick(이하 "서비스")의 이용 조건과 절차, 이용자와 운영자의 권리 · 의무를 정합니다. 서비스는 개인 포트폴리오 프로젝트로 제공되는 데모 서비스입니다.'],
  ['제2조 (서비스 내용)', '서비스는 이용자가 업로드한 문서에서 텍스트를 추출하고, AI 로 항목을 정형화한 뒤, 이용자가 검수한 값을 엑셀 원장 또는 데모 ERP 화면에 자동 입력하는 기능을 제공합니다.'],
  ['제3조 (계정과 권한)', '계정은 일반 사용자, 테스트 관리자(읽기 전용), 운영 관리자로 구분됩니다. 로그인 화면에 공개된 테스트 계정은 누구나 사용할 수 있으므로 개인 정보나 실제 업무 문서를 올리지 마십시오.'],
  ['제4조 (이용자의 의무)', '이용자는 본인에게 권한이 있는 문서만 업로드해야 하며, 타인의 개인정보 · 영업비밀이 담긴 문서를 동의 없이 업로드해서는 안 됩니다.'],
  ['제5조 (AI 결과의 한계)', 'AI 추출 결과는 틀릴 수 있습니다. 서비스는 검수 화면을 제공하며, 최종 입력값의 정확성 확인 책임은 이용자에게 있습니다.'],
  ['제6조 (서비스 변경 · 중단)', '데모 서비스 특성상 사전 고지 없이 기능이 변경되거나, 무료 클라우드 환경의 제약으로 일시 중단 · 지연될 수 있습니다.'],
  ['제7조 (데이터 보존)', '업로드 원본 파일은 서버 재배포 시 삭제될 수 있으며, 운영자는 데모 데이터를 정리하기 위해 계정과 문서를 삭제할 수 있습니다.'],
]

const PRIVACY = [
  ['1. 수집하는 항목', '이메일, 이름, 비밀번호 해시(이메일 가입 시), 소셜 로그인 식별자(Google · 네이버 · 카카오), 최근 로그인 시각, 이용자가 업로드한 문서와 추출 결과.'],
  ['2. 이용 목적', '회원 식별과 로그인, 문서 해석 · 검수 · 자동 입력 기능 제공, 처리 현황 통계(파싱 · RPA 성공률) 산출.'],
  ['3. 제3자 전송', '문서 해석을 위해 문서 텍스트 또는 파일이 Google Gemini API 로 전송될 수 있습니다. 소셜 로그인 시 해당 제공자로부터 이메일 · 이름 등 프로필 정보를 받습니다.'],
  ['4. 저장 위치', '회원 · 문서 메타데이터와 추출 결과는 TiDB Cloud(데이터베이스)에, 영수증 자동 입력의 업로드 원본은 서비스 서버(Render) 디스크에 저장됩니다. AI 도구(견적서 비교 · 계약서 빨간펜 · 건강검진 추이)는 원본 파일을 저장하지 않고 분석 결과만 본인 계정에 보관하며, 관리자 화면에도 노출하지 않습니다.'],
  ['5. 보관 기간', '회원 탈퇴 요청 또는 데모 데이터 정리 시까지 보관합니다. 업로드 원본은 서버 재배포 시 삭제될 수 있습니다.'],
  ['6. 이용자의 권리', '본인 문서는 언제든지 직접 삭제할 수 있으며, 대시보드 하단의 회원 탈퇴로 계정과 모든 데이터(문서 · 분석 기록 · 작업 이력 · 엑셀 원장)를 즉시 삭제할 수 있습니다.'],
  ['7. 보호 조치', '비밀번호는 PBKDF2-SHA256 으로 해시해 저장하고, 데이터베이스 접속은 TLS 로 암호화하며, 관리자 기능은 역할 기반 권한으로 제한합니다.'],
  ['8. 민감 정보 주의', '건강검진 결과와 계약서는 민감한 정보입니다. 공개 테스트 계정은 여러 사람이 함께 쓰므로 실제 문서를 올리지 말고 제공되는 가상 샘플을 사용해 주세요.'],
  ['9. 문의', '개인정보 관련 문의는 GitHub Issues(github.com/fsclass-n/datapick/issues)로 접수합니다. 운영 책임자: 홍기흥.'],
]

function PolicyPage({ title, intro, sections }) {
  return (
    <article className="mx-auto max-w-3xl">
      <p className="eyebrow">Policy</p>
      <h1 className="mt-3 text-3xl font-bold sm:text-title">{title}</h1>
      <p className="mt-3 text-caption text-slate-400">시행일 {UPDATED}</p>
      <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-body text-amber-800">{intro}</p>
      <div className="mt-10 space-y-8">
        {sections.map(([heading, body]) => (
          <section key={heading}>
            <h2 className="text-heading font-semibold">{heading}</h2>
            <p className="mt-2 text-body text-slate-600">{body}</p>
          </section>
        ))}
      </div>
      <div className="mt-12 flex gap-3 border-t border-slate-200 pt-6 text-sm">
        <Link to="/terms" className="font-medium text-brand-600 hover:underline">이용약관</Link>
        <span className="text-slate-300">|</span>
        <Link to="/privacy" className="font-medium text-brand-600 hover:underline">개인정보처리방침</Link>
      </div>
    </article>
  )
}

export function Terms() {
  return <PolicyPage title="이용약관" intro="datapick 은 개인 포트폴리오용 데모 서비스입니다. 실제 업무 문서나 민감한 개인정보는 업로드하지 마십시오." sections={TERMS} />
}

export function Privacy() {
  return <PolicyPage title="개인정보처리방침" intro="업로드한 문서는 AI 해석을 위해 Google Gemini API 로 전송될 수 있습니다. 공개 테스트 계정에 올린 문서는 다른 체험자에게도 보일 수 있습니다." sections={PRIVACY} />
}
