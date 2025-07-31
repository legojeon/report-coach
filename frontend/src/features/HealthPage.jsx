import React, { useState, useEffect } from 'react';

function HealthPage() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHealthData = async () => {
      try {
        setLoading(true);
        const response = await fetch('/health');
        if (!response.ok) {
          throw new Error('Health check failed');
        }
        const data = await response.json();
        setHealthData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchHealthData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">서버 상태 확인 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">서버 연결 실패</h1>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">서버 상태</h1>
          
          {/* 상태 표시 */}
          <div className="mb-6">
            <div className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium ${
              healthData.status === 'healthy' ? 'bg-green-100 text-green-800' :
              healthData.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              <span className={`w-3 h-3 rounded-full mr-2 ${
                healthData.status === 'healthy' ? 'bg-green-500' :
                healthData.status === 'warning' ? 'bg-yellow-500' :
                'bg-red-500'
              }`}></span>
              {healthData.status === 'healthy' ? '정상' :
               healthData.status === 'warning' ? '경고' : '오류'}
            </div>
          </div>

          {/* 기본 정보 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">기본 정보</h3>
              <div className="space-y-2 text-sm">
                <div><span className="font-medium">서비스:</span> {healthData.service}</div>
                <div><span className="font-medium">버전:</span> {healthData.version}</div>
                <div><span className="font-medium">포트:</span> {healthData.port}</div>
                <div><span className="font-medium">시간:</span> {new Date(healthData.timestamp).toLocaleString()}</div>
              </div>
            </div>

            {/* 환경변수 상태 */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">환경변수 상태</h3>
              <div className="space-y-2 text-sm">
                {Object.entries(healthData.environment_variables || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="font-medium">{key}:</span>
                    <span className={`${
                      value === 'configured' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {value === 'configured' ? '설정됨' : '누락'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 디스크 사용량 */}
          {healthData.disk_usage && typeof healthData.disk_usage === 'object' && (
            <div className="bg-gray-50 p-4 rounded-lg mb-6">
              <h3 className="font-semibold text-gray-900 mb-2">디스크 사용량</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium">총 용량:</span> {healthData.disk_usage.total_gb}GB
                </div>
                <div>
                  <span className="font-medium">사용량:</span> {healthData.disk_usage.used_gb}GB
                </div>
                <div>
                  <span className="font-medium">여유 공간:</span> {healthData.disk_usage.free_gb}GB
                </div>
                <div>
                  <span className="font-medium">사용률:</span> {healthData.disk_usage.percent}%
                </div>
              </div>
              {/* 사용률 바 */}
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      healthData.disk_usage.percent > 90 ? 'bg-red-500' :
                      healthData.disk_usage.percent > 80 ? 'bg-yellow-500' :
                      'bg-green-500'
                    }`}
                    style={{ width: `${healthData.disk_usage.percent}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          {/* 경고 정보 */}
          {healthData.missing_env_vars && healthData.missing_env_vars.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
              <h3 className="font-semibold text-yellow-800 mb-2">⚠️ 누락된 환경변수</h3>
              <ul className="list-disc list-inside text-sm text-yellow-700">
                {healthData.missing_env_vars.map((var_name, index) => (
                  <li key={index}>{var_name}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 에러 정보 */}
          {healthData.error && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
              <h3 className="font-semibold text-red-800 mb-2">❌ 오류</h3>
              <p className="text-sm text-red-700">{healthData.error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HealthPage; 