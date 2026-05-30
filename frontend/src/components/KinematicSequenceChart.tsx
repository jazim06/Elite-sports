import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { Activity } from 'lucide-react';

interface KinematicSequenceChartProps {
  data: {
    frame: number;
    hip_vel: number;
    shoulder_vel: number;
    elbow_vel: number;
  }[];
}

const KinematicSequenceChart: React.FC<KinematicSequenceChartProps> = ({ data }) => {
  // We only want to show the last N frames to keep the chart readable
  const displayData = useMemo(() => {
    return data.slice(-30);
  }, [data]);

  return (
    <div className="bg-[#1a1c23] rounded-xl p-4 border border-white/5 flex flex-col h-full relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      
      <div className="flex items-center justify-between mb-4 relative z-10">
        <h3 className="text-sm font-semibold text-white/80 uppercase tracking-wider flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          Kinematic Sequence
        </h3>
        <span className="text-[10px] text-white/40 px-2 py-1 bg-white/5 rounded-full">
          Ang. Vel (deg/f)
        </span>
      </div>

      <div className="flex-1 w-full min-h-[160px] relative z-10">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={displayData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis dataKey="frame" hide />
            <YAxis 
              tick={{ fill: '#ffffff50', fontSize: 10 }} 
              axisLine={false} 
              tickLine={false} 
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1a1c23', border: '1px solid #ffffff10', borderRadius: '8px' }}
              labelStyle={{ display: 'none' }}
              itemStyle={{ fontSize: '12px' }}
            />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '10px' }} />
            <Line 
              type="monotone" 
              name="Hip"
              dataKey="hip_vel" 
              stroke="#ef4444" 
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line 
              type="monotone" 
              name="Shoulder"
              dataKey="shoulder_vel" 
              stroke="#3b82f6" 
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line 
              type="monotone" 
              name="Elbow"
              dataKey="elbow_vel" 
              stroke="#22c55e" 
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-2 text-xs text-white/50 text-center relative z-10">
        Optimal sequence peaks: Hip ➔ Shoulder ➔ Arm
      </div>
    </div>
  );
};

export default KinematicSequenceChart;
