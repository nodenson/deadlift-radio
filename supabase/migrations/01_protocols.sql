-- 01_protocols.sql
CREATE TABLE protocol_days (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  protocol_id UUID REFERENCES protocols(id) ON DELETE CASCADE,
  week_number INTEGER NOT NULL,
  day_label TEXT NOT NULL,
  notes TEXT
);
ALTER TABLE protocol_days ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view protocol days" ON protocol_days FOR SELECT USING (true);

CREATE TABLE prescribed_sets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  protocol_day_id UUID REFERENCES protocol_days(id) ON DELETE CASCADE,
  exercise TEXT NOT NULL,
  load_pct REAL,
  load_fixed REAL,
  reps TEXT NOT NULL,
  sets INTEGER NOT NULL,
  rest_seconds INTEGER,
  rpe_start REAL,
  rpe_end REAL,
  notes TEXT,
  sort_order INTEGER DEFAULT 0
);
ALTER TABLE prescribed_sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view prescribed sets" ON prescribed_sets FOR SELECT USING (true);

CREATE TABLE protocol_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  protocol_id UUID REFERENCES protocols(id) ON DELETE CASCADE,
  start_date DATE NOT NULL,
  current_max REAL,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE protocol_enrollments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own enrollments" ON protocol_enrollments
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Command can view all enrollments" ON protocol_enrollments
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'command')
  );
