-- 00_init.sql
-- Supabase Schema for Deadlift Radio Mobile MVP

-- Profiles Table (Linked to auth.users)
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT NOT NULL,
  role TEXT CHECK (role IN ('command', 'warrior')) DEFAULT 'warrior',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Warriors can read their own profile
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

-- Command can read all profiles
CREATE POLICY "Command can view all profiles" ON profiles
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'command'
    )
  );

-- Sessions Table
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) NOT NULL,
  date DATE NOT NULL,
  bodyweight REAL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own sessions" ON sessions
  FOR ALL USING (auth.uid() = user_id);

-- Exercises Table
CREATE TABLE exercises (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own exercises" ON exercises
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM sessions WHERE sessions.id = exercises.session_id AND sessions.user_id = auth.uid()
    )
  );

-- Sets Table
CREATE TABLE sets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
  load REAL NOT NULL,
  reps INTEGER NOT NULL,
  effort TEXT,
  pain TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE sets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own sets" ON sets
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM exercises
      JOIN sessions ON exercises.session_id = sessions.id
      WHERE exercises.id = sets.exercise_id AND sessions.user_id = auth.uid()
    )
  );

-- Protocols Table
CREATE TABLE protocols (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id UUID REFERENCES profiles(id),
  title TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE protocols ENABLE ROW LEVEL SECURITY;
-- Anyone can view protocols (or just command/warriors)
CREATE POLICY "Anyone can view protocols" ON protocols FOR SELECT USING (true);
CREATE POLICY "Command can create protocols" ON protocols
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'command'
    )
  );
