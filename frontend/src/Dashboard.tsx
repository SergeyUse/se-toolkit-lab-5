import { useEffect, useState } from 'react';
import { Bar, Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

// Типы для API ответов
interface ScoreBucket {
    bucket: string;
    count: number;
}

interface TimelinePoint {
    date: string;
    submissions: number;
}

interface PassRate {
    task: string;
    avg_score: number;
    attempts: number;
}

interface DashboardProps {
    apiKey: string;
}

export default function Dashboard({ apiKey }: DashboardProps) {
    const [selectedLab, setSelectedLab] = useState('lab-04');
    const [scoreData, setScoreData] = useState<ScoreBucket[]>([]);
    const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);
    const [passRates, setPassRates] = useState<PassRate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const labs = ['lab-01', 'lab-02', 'lab-03', 'lab-04', 'lab-05', 'lab-06', 'lab-07', 'lab-08', 'lab-09', 'lab-10'];

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                const headers = {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json',
                };

                const baseUrl = import.meta.env.VITE_API_TARGET || '';

                // Загружаем все три набора данных параллельно
                const [scoresRes, timelineRes, passRatesRes] = await Promise.all([
                    fetch(`${baseUrl}/analytics/scores?lab=${selectedLab}`, { headers }),
                    fetch(`${baseUrl}/analytics/timeline?lab=${selectedLab}`, { headers }),
                    fetch(`${baseUrl}/analytics/pass-rates?lab=${selectedLab}`, { headers })
                ]);

                if (!scoresRes.ok || !timelineRes.ok || !passRatesRes.ok) {
                    throw new Error('Failed to fetch analytics data');
                }

                const scoresData = await scoresRes.json();
                const timelineData = await timelineRes.json();
                const passRatesData = await passRatesRes.json();

                setScoreData(scoresData);
                setTimelineData(timelineData);
                setPassRates(passRatesData);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [selectedLab, apiKey]);

    // Подготовка данных для bar chart (scores)
    const barChartData = {
        labels: scoreData.map(item => item.bucket),
        datasets: [
            {
                label: 'Number of submissions',
                data: scoreData.map(item => item.count),
                backgroundColor: 'rgba(53, 162, 235, 0.5)',
                borderColor: 'rgb(53, 162, 235)',
                borderWidth: 1,
            },
        ],
    };

    // Подготовка данных для line chart (timeline)
    const lineChartData = {
        labels: timelineData.map(item => item.date),
        datasets: [
            {
                label: 'Submissions per day',
                data: timelineData.map(item => item.submissions),
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                tension: 0.1,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top' as const,
            },
        },
    };

    if (loading) return <div className="loading">Loading dashboard data...</div>;
    if (error) return <div className="error">Error: {error}</div>;

    return (
        <div className="dashboard">
            <h1>Analytics Dashboard</h1>

            <div className="lab-selector">
                <label htmlFor="lab-select">Select Lab: </label>
                <select
                    id="lab-select"
                    value={selectedLab}
                    onChange={(e) => setSelectedLab(e.target.value)}
                >
                    {labs.map(lab => (
                        <option key={lab} value={lab}>{lab}</option>
                    ))}
                </select>
            </div>

            <div className="charts-grid">
                <div className="chart-container">
                    <h2>Score Distribution</h2>
                    <div style={{ height: '300px' }}>
                        <Bar data={barChartData} options={chartOptions} />
                    </div>
                </div>

                <div className="chart-container">
                    <h2>Submissions Timeline</h2>
                    <div style={{ height: '300px' }}>
                        <Line data={lineChartData} options={chartOptions} />
                    </div>
                </div>
            </div>

            <div className="table-container">
                <h2>Pass Rates by Task</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Task</th>
                            <th>Average Score</th>
                            <th>Attempts</th>
                        </tr>
                    </thead>
                    <tbody>
                        {passRates.map((item, index) => (
                            <tr key={index}>
                                <td>{item.task}</td>
                                <td>{item.avg_score.toFixed(1)}</td>
                                <td>{item.attempts}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}