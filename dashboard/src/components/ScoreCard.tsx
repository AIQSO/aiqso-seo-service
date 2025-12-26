'use client';

interface ScoreCardProps {
  title: string;
  score: number | null;
  change?: number | null;
  subtitle?: string;
}

export default function ScoreCard({ title, score, change, subtitle }: ScoreCardProps) {
  const getScoreColor = (s: number) => {
    if (s >= 80) return 'text-green-600';
    if (s >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getChangeColor = (c: number) => {
    if (c > 0) return 'text-green-600 bg-green-50';
    if (c < 0) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        {change !== undefined && change !== null && (
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${getChangeColor(change)}`}>
            {change > 0 ? '+' : ''}
            {change}
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline">
        <span
          className={`text-3xl font-bold ${score !== null ? getScoreColor(score) : 'text-gray-400'}`}
        >
          {score !== null ? score : 'N/A'}
        </span>
        {score !== null && <span className="ml-1 text-lg text-gray-400">/100</span>}
      </div>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}
