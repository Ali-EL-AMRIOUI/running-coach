'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Session {
  type: string;
  km: number;
  pace: string;
  details: string;
}

interface Day {
  day: number;
  morning: Session;
  afternoon: Session;
}

interface Week {
  week: number;
  phase: string;
  weekly_km: number;
  days: Day[];
}

interface Plan {
  id: number;
  distance: string;
  coach_analysis: string;
  total_km: number;
  weeks: Week[];
  created_at: string;
}

const typeColor: Record<string, string> = {
  RUN:       'bg-green-700',
  LONG_RUN:  'bg-purple-700',
  INTERVALS: 'bg-red-700',
  TEMPO:     'bg-yellow-600',
  STRENGTH:  'bg-blue-700',
  REST:      'bg-gray-700',
};

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function PlanDetailPage() {
  const params  = useParams();
  const [plan, setPlan]       = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [openWeek, setOpenWeek] = useState<number>(1);

  useEffect(() => {
    const fetchPlan = async () => {
      try {
        const id = parseInt(params.id as string);
        if (isNaN(id)) throw new Error('Invalid ID');
        const data = await api.getPlan(id);
        setPlan(data);
      } catch (err: any) {
        setError(err.message || 'Plan not found');
      } finally {
        setLoading(false);
      }
    };
    fetchPlan();
  }, [params.id]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
      <div className="text-center">
        <div className="animate-spin text-4xl mb-4">G</div>
        <p>Loading plan...</p>
      </div>
    </div>
  );

  if (error || !plan) return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900">
      <div className="text-red-400 text-xl mb-4">{error || 'Plan not found'}</div>
      <Link href="/dashboard" className="text-blue-400 hover:underline">Dashboard</Link>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <Link href="/dashboard" className="text-blue-400 hover:underline text-sm">
            Dashboard
          </Link>
          <h1 className="text-3xl font-bold text-white mt-2">
            Plan {plan.distance}
          </h1>
          <p className="text-gray-400 mt-1">
            {plan.weeks?.length} weeks • {plan.total_km} total km
          </p>
        </div>

        {/* Coach Analysis */}
        {plan.coach_analysis && (
          <div className="bg-gray-800 rounded-xl p-6 mb-8 border-l-4 border-blue-500">
            <h2 className="text-lg font-bold text-blue-400 mb-2">
              Coach Analysis
            </h2>
            <p className="text-gray-300 text-sm leading-relaxed">
              {plan.coach_analysis}
            </p>
          </div>
        )}

        {/* Volume summary */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {plan.weeks?.slice(0, 4).map((week) => (
            <div key={week.week} className="bg-gray-800 rounded-lg p-4 text-center">
              <div className="text-xs text-gray-400 mb-1">Week {week.week}</div>
              <div className="text-xl font-bold text-white">{week.weekly_km}</div>
              <div className="text-xs text-gray-500">km</div>
              <div className="text-xs text-blue-400 mt-1">{week.phase}</div>
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="space-y-4">
          {plan.weeks?.map((week) => (
            <div key={week.week} className="bg-gray-800 rounded-xl overflow-hidden">

              {/* Week header */}
              <button
                onClick={() => setOpenWeek(openWeek === week.week ? 0 : week.week)}
                className="w-full flex justify-between items-center p-4 hover:bg-gray-750 transition"
              >
                <div className="flex items-center gap-4">
                  <span className="text-white font-bold">Week {week.week}</span>
                  <span className="text-xs bg-blue-700 text-white px-2 py-1 rounded">
                    {week.phase}
                  </span>
                  <span className="text-gray-400 text-sm">{week.weekly_km} km</span>
                </div>
                <span className="text-gray-400">
                  {openWeek === week.week ? '▲' : '▼'}
                </span>
              </button>

              {/* Days */}
              {openWeek === week.week && (
                <div className="p-4 space-y-3">
                  {week.days?.map((day) => (
                    <div key={day.day} className="bg-gray-900 rounded-lg p-4">
                      <div className="text-gray-400 text-sm font-bold mb-3">
                        {dayNames[day.day - 1] || `Day ${day.day}`}
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        {/* Morning */}
                        <SessionCard
                          label="Morning"
                          session={day.morning}
                        />
                        {/* Afternoon */}
                        <SessionCard
                          label="Afternoon"
                          session={day.afternoon}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

function SessionCard({ label, session }: { label: string; session: Session }) {
  const typeColor: Record<string, string> = {
    RUN:       'bg-green-700',
    LONG_RUN:  'bg-purple-700',
    INTERVALS: 'bg-red-700',
    TEMPO:     'bg-yellow-600',
    STRENGTH:  'bg-blue-700',
    REST:      'bg-gray-700',
  };

  const isRest = !session || session.type === 'REST';

  return (
    <div className="bg-gray-800 rounded p-3">
      <div className="text-xs text-gray-500 mb-2">{label}</div>
      <span className={`text-xs px-2 py-1 rounded text-white ${typeColor[session?.type] || 'bg-gray-600'}`}>
        {session?.type || 'REST'}
      </span>
      {!isRest && (
        <>
          <p className="text-white text-sm mt-2 font-bold">
            {session.km > 0 ? `${session.km} km` : ''} 
            {session.pace && session.pace !== 'N/A' ? ` • ${session.pace}` : ''}
          </p>
          <p className="text-gray-400 text-xs mt-1 leading-relaxed">
            {session.details}
          </p>
        </>
      )}
    </div>
  );
}