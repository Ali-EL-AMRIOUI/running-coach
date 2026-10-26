'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Plan {
  id: number;
  distance: string;
  weeks: number;
  total_km: number;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [plans, setPlans]     = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      router.push('/login');
      return;
    }
    api.getPlans()
      .then(setPlans)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-900">
      Loading...
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-800">AI Running Coach</h2>
          <button
            onClick={() => { localStorage.removeItem('token'); router.push('/'); }}
            className="text-gray-500 hover:text-red-600 text-sm"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex justify-between items-center mb-10">
          <h1 className="text-2xl font-bold text-gray-900">My training plans</h1>
          <Link
            href="/generate"
            className="bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition"
          >
            + New plan
          </Link>
        </div>

        {plans.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-gray-300">
            <p className="text-gray-500 mb-4">No plan found.</p>
            <Link href="/generate" className="text-blue-600 font-semibold hover:underline">
              Start now →
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition"
              >
                <div className="text-xs font-bold text-blue-600 uppercase mb-2">
                  Goal
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-4">
                  {plan.distance}
                </h3>
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>{plan.weeks} weeks</span>
                  <span className="font-semibold">{plan.total_km} km</span>
                </div>
                {plan.created_at && (
                  <div className="text-xs text-gray-400 mb-4">
                    Created on {new Date(plan.created_at).toLocaleDateString()}
                  </div>
                )}
                <Link
                  href={`/plan/${plan.id}`}
                  className="block text-center text-sm text-gray-900 font-medium border border-gray-300 py-2 rounded-lg hover:bg-gray-50 transition"
                >
                  Open plan →
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}