import React, { useState, useMemo } from 'react';
import { Microscope } from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

export default function LabTrendChart({ labTrends = {}, otherLabResults = [] }) {
  const testNames = Object.keys(labTrends);
  
  // Find test with most data points for default
  const defaultTest = useMemo(() => {
    if (testNames.length === 0) return null;
    return testNames.reduce((prev, current) => 
      (labTrends[current]?.length > labTrends[prev]?.length) ? current : prev
    );
  }, [testNames, labTrends]);

  const [selectedTest, setSelectedTest] = useState(defaultTest);

  // Fallback to default if selected is removed or invalid
  const currentTest = testNames.includes(selectedTest) ? selectedTest : defaultTest;
  const chartData = currentTest ? labTrends[currentTest] : [];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isAbnormal = ["High", "Low", "Abnormal"].includes(data.flag);
      return (
        <div className="bg-surface-container-high border border-outline-variant/30 p-3 rounded-lg shadow-md text-sm">
          <p className="font-semibold text-on-surface mb-1">{data.date}</p>
          <p className="text-on-surface">
            Value: <span className="font-bold">{data.value} {data.unit}</span>
          </p>
          {data.flag && (
            <p className={`mt-1 font-bold ${isAbnormal ? 'text-error' : 'text-primary'}`}>
              Flag: {data.flag}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  const renderOtherLabs = () => {
    if (!otherLabResults || otherLabResults.length === 0) return null;
    return (
      <div className="mt-4 border-t border-outline-variant/20 pt-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant/70 mb-3">Other Results</h4>
        <ul className="flex flex-col gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
          {otherLabResults.map((l, idx) => (
            <li key={l.id || idx} className="bg-surface-container-high rounded-lg p-2 text-sm">
              <div className="text-on-surface font-medium">{l.raw_text || l.test_name}</div>
              {l.loinc_code && <div className="text-xs text-on-surface-variant mt-1">LOINC: {l.loinc_code}</div>}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-4 shadow-sm flex flex-col h-full min-h-[350px]">
      <h3 className="flex items-center gap-2 text-on-surface font-semibold mb-3 border-b border-outline-variant/20 pb-2">
        <Microscope size={16} className="text-violet-500" /> Lab Results
      </h3>

      {testNames.length === 0 ? (
        <div className="flex-1 flex flex-col">
          <p className="text-sm text-on-surface-variant/70 italic text-center mt-4 mb-2">
            No lab results recorded.
          </p>
          {renderOtherLabs()}
        </div>
      ) : (
        <div className="flex-1 flex flex-col">
          <div className="flex flex-wrap gap-2 mb-4">
            {testNames.map(name => {
              const isActive = name === currentTest;
              const isSingle = testNames.length === 1;
              return (
                <button
                  key={name}
                  onClick={() => !isSingle && setSelectedTest(name)}
                  className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-colors ${
                    isActive 
                      ? 'bg-primary/10 text-primary border-primary/30 shadow-sm' 
                      : 'bg-surface-variant text-on-surface-variant border-outline-variant/20 hover:bg-surface-variant/80'
                  } ${isSingle ? 'cursor-default' : 'cursor-pointer'}`}
                >
                  {name}
                </button>
              );
            })}
          </div>
          
          <div className="flex-1 min-h-[250px] w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="var(--text-muted)" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickMargin={10}
                />
                <YAxis 
                  stroke="var(--text-muted)" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => val}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)' }} />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="var(--primary-cyan)" 
                  strokeWidth={2}
                  activeDot={{ r: 6, fill: "var(--primary-cyan)", stroke: "#131A2B", strokeWidth: 2 }}
                  dot={(props) => {
                    const { cx, cy, payload } = props;
                    const isAbnormal = ["High", "Low", "Abnormal"].includes(payload.flag);
                    return (
                      <circle 
                        key={`${cx}-${cy}`}
                        cx={cx} 
                        cy={cy} 
                        r={4} 
                        fill={isAbnormal ? "var(--accent-rose)" : "var(--primary-cyan)"} 
                        stroke="#131A2B"
                        strokeWidth={1.5}
                      />
                    );
                  }} 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          {renderOtherLabs()}
        </div>
      )}
    </div>
  );
}
