import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMe } from '../services/auth';
import api from '../services/api';

const plansData = [
  {
    name: 'Basic',
    price: 'free',
    unit: 'KRW/월',
    description: '핵심 기능을 무료로 체험해보세요',
    features: [
      '유사 보고서 검색',
      '표준 및 고급 옵션 모델',
      '전체/요약 보고서 열람',
      '검색 기록 및 history 저장',
      '상세 보고서 요약 및 정리'
    ],
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₩10,000',
    unit: 'KRW/월',
    description: 'AI 분석과 작성을 위한 풀 서비스 경험',
    features: [
      '모든 Basic 기능 포함',
      '보고서 작성 코칭 및 보조',
      '최신 모델에 무제한 액세스',
      '유사 보고서 검색 및 AI 분석 제공',
      '상세보고서 기반 질의응답',
      'AI와 대화하며 보고서 심층 분석'
    ],
    highlight: true,
  },
];

function PlanPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const data = await getMe(token);
        setUser(data);
      } catch (err) {
        console.error('getMe 에러:', err);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  const handleBack = () => {
    navigate('/');
  };

  // 플랜 변경 핸들러
  const handlePlanChange = async (toMembership) => {
    if (!user || !user.id) {
      navigate('/login');
      return;
    }
    setUpdating(true);
    try {
      const token = localStorage.getItem('token');
      
      await api.put(`/users/${user.id}`, { is_membership: toMembership }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // 변경 후 상태 갱신
      const data = await getMe(token);
      setUser(data);
    } catch (err) {
      console.error('플랜 변경 에러:', err);
      console.error('에러 응답:', err.response?.data);
      const errorMessage = err.response?.data?.detail || '플랜 변경에 실패했습니다.';
      alert(errorMessage);
    } finally {
      setUpdating(false);
    }
  };

  // 플랜 CTA 동적 결정
  const plans = plansData.map((plan, idx) => {
    let cta = plan.highlight ? 'Pro 이용하기' : '나의 현재 플랜';
    let disabled = false;
    let onClick = undefined;
    if (user) {
      if (!user.is_membership && !plan.highlight) {
        cta = '나의 현재 플랜';
        disabled = true;
      } else if (user.is_membership && plan.highlight) {
        cta = '나의 현재 플랜';
        disabled = true;
      } else {
        cta = plan.highlight ? 'Pro 이용하기' : 'Pro 해지하기';
        disabled = updating || !user.id;
        onClick = () => handlePlanChange(plan.highlight);
      }
    } else {
      // 비로그인 시 모두 업그레이드로
      cta = plan.highlight ? 'Pro 이용하기' : 'basic 이용하기';
      disabled = false;
      onClick = () => handlePlanChange(plan.highlight);
    }
    return { ...plan, cta, disabled, onClick };
  });

  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col items-center justify-center py-8 px-2 relative w-full">
      {/* 왼쪽 상단 뒤로가기 버튼 */}
      <button onClick={handleBack} className="absolute left-4 top-4 text-neutral-400 hover:text-primary-400 text-xs">← 뒤로</button>
      {/* 상단 타이틀 */}
      <h1 className="text-2xl font-bold mb-6">플랜 업그레이드</h1>
      {/* 상단 여백 */}
      <div className="mb-10" />
      {/* 플랜 카드 */}
      <div className="w-full max-w-3xl grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        {plans.map((plan, idx) => (
          <div
            key={plan.name}
            className={`flex flex-col rounded-2xl border ${plan.highlight ? 'border-primary-500 shadow-xl scale-105' : 'border-gray-200'} bg-white p-8 transition-all duration-200`}
          >
            <div className="text-lg font-bold mb-1">{plan.name}</div>
            <div className="flex items-end mb-2">
              <span className="text-3xl font-bold mr-1">{plan.price}</span>
              <span className="text-base text-neutral-400">{plan.unit}</span>
            </div>
            <div className="text-sm text-gray-500 mb-6">{plan.description}</div>
            <button
              className={`w-full py-3 rounded-lg font-semibold text-sm mb-6 transition-colors duration-200 ${plan.highlight ? 'bg-primary-600 text-white hover:bg-primary-700' : 'bg-primary-100 text-primary-600'} ${plan.disabled ? 'cursor-default opacity-60' : ''}`}
              disabled={plan.disabled}
              onClick={plan.onClick}
            >
              {plan.cta}
            </button>
            <ul className="mb-2 space-y-2">
              {plan.features.map((f, i) => (
                <li key={i} className="flex items-center text-sm text-gray-700">
                  <svg className="w-4 h-4 text-primary-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  {f}
                </li>
              ))}
            </ul>
            {plan.highlight && <div className="mt-4 text-xs text-gray-400">* Pro 플랜은 대회준비 및 보고서 작성에 적합합니다.</div>}
          </div>
        ))}
      </div>
      {/* 하단 안내 */}
      <div className="mt-8 text-center text-gray-400 text-xs">결제, 환불 등 문의는 메일을 통해 안내받으실 수 있습니다.</div>
      <div className="mt-2 text-center text-gray-500 text-xs">비즈니스에 더 많은 기능이 필요하신가요? <span className="underline cursor-pointer">Enterprise 문의</span></div>
    </div>
  );
}

export default PlanPage; 