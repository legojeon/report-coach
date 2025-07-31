-- ReportCoach Database Schema
-- Supabase SQL Editor에서 실행하여 테이블을 생성합니다.

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT,
  affiliation TEXT,
  is_membership BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- AI 사용량 로그 테이블
CREATE TABLE IF NOT EXISTS public.ai_usage_logs (
  request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  session_id UUID,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  service_name TEXT NOT NULL,
  nttSn INTEGER,
  request_prompt TEXT NOT NULL,
  request_token_count INTEGER NOT NULL,
  response_token_count INTEGER NOT NULL,
  total_token_count INTEGER NOT NULL,
  
  CONSTRAINT fk_user
    FOREIGN KEY (user_id)
    REFERENCES public.users (id)
    ON DELETE CASCADE
);

-- 노트 테이블
CREATE TABLE IF NOT EXISTS public.notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  nttsn INTEGER NOT NULL,
  title TEXT,
  service_name TEXT,
  chat_history JSONB,
  chat_summary TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT fk_user 
    FOREIGN KEY (user_id)
    REFERENCES public.users (id)
    ON DELETE CASCADE
);

-- 인덱스 생성 (선택사항)
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_user_id ON public.ai_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_timestamp ON public.ai_usage_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON public.notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_nttsn ON public.notes(nttsn); 