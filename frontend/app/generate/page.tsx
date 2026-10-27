'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function GeneratePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    age: '',
    gender: 'M',
    age_start: '',
    years_practice: '',
    other_sports: '',
    record_400m: '',
    record_800m: '',
    record_1500m: '',
    record_5000m: '',
    record_10000m: '',
    record_half: '',
    record_marathon: '',
    current_volume: '',
    current_frequency: '',
    volume_s4: '',
    volume_s3: '',
    volume_s2: '',
    volume_s1: '',
    last_week_training: '',
    goal_distance: 'marathon',
    goal_time: '',
    goal_date: '',
    availability: '',
    double_session: 'no',
    double_session_days: '',
    last_injury: '',
    return_date: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        age: parseInt(form.age),
        gender: form.gender,
        age_start: form.age_start ? parseInt(form.age_start) : null,
        years_practice: form.years_practice ? parseInt(form.years_practice) : null,
        other_sports: form.other_sports || null,
        record_400m: form.record_400m || null,
        record_800m: form.record_800m || null,
        record_1500m: form.record_1500m || null,
        record_5000m: form.record_5000m || null,
        record_10000m: form.record_10000m || null,
        record_half: form.record_half || null,
        record_marathon: form.record_marathon || null,
        current_volume: parseFloat(form.current_volume),
        current_frequency: parseInt(form.current_frequency),
        volume_s4: form.volume_s4 ? parseFloat(form.volume_s4) : null,
        volume_s3: form.volume_s3 ? parseFloat(form.volume_s3) : null,
        volume_s2: form.volume_s2 ? parseFloat(form.volume_s2) : null,
        volume_s1: form.volume_s1 ? parseFloat(form.volume_s1) : null,
        last_week_training: form.last_week_training || null,
        goal_distance: form.goal_distance,
        goal_time: form.goal_time || null,
        goal_date: form.goal_date,
        availability: parseInt(form.availability),
        double_session: form.double_session,
        double_session_days: form.double_session_days || null,
        last_injury: form.last_injury || null,
        return_date: form.return_date || null,
      };
      const plan = await api.generatePlan(payload);
      router.push(`/plan/${plan.id}`);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Generate Your Personalized Plan</h1>
        
        <form onSubmit={handleSubmit} className="bg-gray-800 p-6 rounded-2xl space-y-6">
          
          {/* 1. IDENTITY & HISTORY */}
          <div className="border-b border-gray-700 pb-4">
            <h2 className="text-xl font-bold text-green-400 mb-4">1. Identity & History</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-gray-400 mb-1">Age *</label><input type="number" name="age" value={form.age} onChange={handleChange} className="input w-full" required /></div>
              <div><label className="block text-gray-400 mb-1">Gender *</label><select name="gender" value={form.gender} onChange={handleChange} className="input w-full"><option value="M">Male</option><option value="F">Female</option></select></div>
              <div><label className="block text-gray-400 mb-1">Age started athletics</label><input type="number" name="age_start" value={form.age_start} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Years of practice</label><input type="number" name="years_practice" value={form.years_practice} onChange={handleChange} className="input w-full" /></div>
              <div className="col-span-2"><label className="block text-gray-400 mb-1">Other sports practiced</label><input type="text" name="other_sports" placeholder="Swimming (10 years)" value={form.other_sports} onChange={handleChange} className="input w-full" /></div>
            </div>
          </div>

          {/* 2. PERSONAL RECORDS */}
          <div className="border-b border-gray-700 pb-4">
            <h2 className="text-xl font-bold text-blue-400 mb-4">2. Personal Records</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-gray-400 mb-1">400m</label><input type="text" name="record_400m" placeholder="ss" value={form.record_400m} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">800m</label><input type="text" name="record_800m" placeholder="mm:ss" value={form.record_800m} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">1500m</label><input type="text" name="record_1500m" placeholder="mm:ss" value={form.record_1500m} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">5000m</label><input type="text" name="record_5000m" placeholder="mm:ss" value={form.record_5000m} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">10000m</label><input type="text" name="record_10000m" placeholder="mm:ss" value={form.record_10000m} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Half marathon</label><input type="text" name="record_half" placeholder="hh:mm:ss" value={form.record_half} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Marathon</label><input type="text" name="record_marathon" placeholder="hh:mm:ss" value={form.record_marathon} onChange={handleChange} className="input w-full" /></div>
            </div>
          </div>

          {/* 3. CURRENT TRAINING LOAD */}
          <div className="border-b border-gray-700 pb-4">
            <h2 className="text-xl font-bold text-blue-400 mb-4">3. Current Training Load</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-gray-400 mb-1">Current volume (km/week) *</label><input type="number" name="current_volume" value={form.current_volume} onChange={handleChange} className="input w-full" required /></div>
              <div><label className="block text-gray-400 mb-1">Current frequency (sessions/week) *</label><input type="number" name="current_frequency" value={form.current_frequency} onChange={handleChange} className="input w-full" required /></div>
              <div><label className="block text-gray-400 mb-1">Volume week -4 (km)</label><input type="number" name="volume_s4" value={form.volume_s4} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Volume week -3 (km)</label><input type="number" name="volume_s3" value={form.volume_s3} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Volume week -2 (km)</label><input type="number" name="volume_s2" value={form.volume_s2} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Volume week -1 (km)</label><input type="number" name="volume_s1" value={form.volume_s1} onChange={handleChange} className="input w-full" /></div>
              <div className="col-span-2"><label className="block text-gray-400 mb-1">Last week training</label><textarea name="last_week_training" value={form.last_week_training} onChange={handleChange} rows={2} className="input w-full" placeholder="2 easy runs, 1 interval, 1 long run" /></div>
            </div>
          </div>

          {/* 4. GOAL */}
          <div className="border-b border-gray-700 pb-4">
            <h2 className="text-xl font-bold text-blue-400 mb-4">4. Goal</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-gray-400 mb-1">Target distance *</label><select name="goal_distance" value={form.goal_distance} onChange={handleChange} className="input w-full"><option value="5k">5 km</option><option value="10k">10 km</option><option value="half-marathon">Half marathon</option><option value="marathon">Marathon</option></select></div>
              <div><label className="block text-gray-400 mb-1">Target time</label><input type="text" name="goal_time" placeholder="hh:mm:ss" value={form.goal_time} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Goal date *</label><input type="date" name="goal_date" value={form.goal_date} onChange={handleChange} className="input w-full" required /></div>
              <div><label className="block text-gray-400 mb-1">Availability (sessions/week) *</label><input type="number" name="availability" value={form.availability} onChange={handleChange} className="input w-full" required /></div>
              <div><label className="block text-gray-400 mb-1">Double session possible?</label><select name="double_session" value={form.double_session} onChange={handleChange} className="input w-full"><option value="no">No</option><option value="yes">Yes</option></select></div>
              <div><label className="block text-gray-400 mb-1">If yes, which days?</label><input type="text" name="double_session_days" placeholder="tuesday, thursday" value={form.double_session_days} onChange={handleChange} className="input w-full" /></div>
            </div>
          </div>

          {/* 5. HEALTH */}
          <div className="pb-4">
            <h2 className="text-xl font-bold text-blue-400 mb-4">5. Health</h2>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-gray-400 mb-1">Last injury</label><input type="text" name="last_injury" placeholder="None / Tendinitis (2025)" value={form.last_injury} onChange={handleChange} className="input w-full" /></div>
              <div><label className="block text-gray-400 mb-1">Return date after break</label><input type="date" name="return_date" value={form.return_date} onChange={handleChange} className="input w-full" /></div>
            </div>
          </div>

          <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition disabled:opacity-50">
            {loading ? 'Generating...' : 'Generate My Plan'}
          </button>
        </form>
      </div>
    </div>
  );
}