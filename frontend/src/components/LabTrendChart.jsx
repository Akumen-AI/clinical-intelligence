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
        <div className="bg-surface border border-line p-3 rounded-lg shadow-sm text-sm">
          <p className="font-semibold text-ink mb-1">{data.date}</p>
          <p className="text-ink">
            Value: <span className="font-bold">{data.value} {data.unit}</span>
          </p>
          {data.flag && (
            <p className={`mt-1 font-bold ${isAbnormal ? 'text-danger' : 'text-teal'}`}>
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
      <div className="mt-4 border-t border-line pt-4">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate mb-3">Other Results</h4>
        <ul className="flex flex-col gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
          {otherLabResults.map((l, idx) => (
            <li key={l.id || idx} className="bg-paper rounded-lg p-2 text-sm border border-line">
              <div className="text-ink font-medium">{l.raw_text || l.test_name}</div>
              {l.loinc_code && <div className="text-[10px] font-mono text-slate mt-1">LOINC: {l.loinc_code}</div>}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="bg-surface rounded-xl border border-line p-4 shadow-sm flex flex-col h-full min-h-[350px]">
      <h3 className="flex items-center gap-2 text-ink font-bold mb-3 border-b border-line pb-2">
        <Microscope size={16} className="text-teal" /> Lab Results
      </h3>

      {testNames.length === 0 ? (
        <div className="flex-1 flex flex-col">
          <p className="text-sm text-slate italic text-center mt-4 mb-2">
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
                      ? 'bg-teal/10 text-teal border-teal/20 shadow-sm' 
                      : 'bg-paper text-slate border-line hover:bg-line/50 hover:text-ink'
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
                <CartesianGrid strokeDasharray="3 3" stroke="#E1E5EA" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#5A6472" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickMargin={10}
                />
                <YAxis 
                  stroke="#5A6472" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => val}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#E1E5EA' }} />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#0B6E6E" 
                  strokeWidth={2}
                  activeDot={{ r: 6, fill: "#0B6E6E", stroke: "#FFFFFF", strokeWidth: 2 }}
                  dot={(props) => {
                    const { cx, cy, payload } = props;
                    const isAbnormal = ["High", "Low", "Abnormal"].includes(payload.flag);
                    return (
                      <circle 
                        key={`${cx}-${cy}`}
                        cx={cx} 
                        cy={cy} 
                        r={4} 
                        fill={isAbnormal ? "#B3261E" : "#0B6E6E"} 
                        stroke="#FFFFFF"
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
