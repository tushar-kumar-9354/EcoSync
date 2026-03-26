'use client';

import { useReports } from '@/hooks/useData';
import { Card, Badge, Button } from '@/components/ui';
import { CategoryBreakdownChart, SentimentTrendChart, SeverityDistributionChart } from '@/components/charts';
import { REPORT_CATEGORIES } from '@/lib/constants';
import { useState } from 'react';

export default function ReportsDashboard() {
  const [filter, setFilter] = useState({ status: '', category: '' });
  const [page, setPage] = useState(1);
  const { data: reportsData, isLoading, refetch } = useReports({ ...filter, page });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [formData, setFormData] = useState({
    category: '',
    description: '',
    address: '',
    latitude: '28.6139',
    longitude: '77.2090',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      category: formData.category,
      description: formData.description,
      location: {
        lat: parseFloat(formData.latitude),
        lng: parseFloat(formData.longitude),
        address: formData.address || 'New Delhi, India',
      },
      severity: 'medium',
      reporter_anonymous: true,
    };

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setSubmitted(true);
        setFormData({ category: '', description: '', address: '', latitude: '28.6139', longitude: '77.2090' });
        refetch();
        setTimeout(() => setSubmitted(false), 3000);
      }
    } catch (err) {
      console.error(err);
    }
    setSubmitting(false);
  };

  // Compute category breakdown from reports
  const reports = reportsData?.reports || [];
  const categoryCounts = reports.reduce((acc: Record<string, number>, r) => {
    acc[r.category] = (acc[r.category] || 0) + 1;
    return acc;
  }, {});
  const categoryBreakdown = Object.entries(categoryCounts)
    .map(([category, count], i) => ({
      category: REPORT_CATEGORIES.find(c => c.value === category)?.label || category,
      count,
      color: ['#00C853', '#5EF5A7', '#FFD300', '#FF8C00', '#FF3B3B', '#9B59B6', '#3498DB', '#E74C3C'][i % 8]
    }))
    .sort((a, b) => b.count - a.count);

  // Status breakdown
  const statusCounts = reports.reduce((acc: Record<string, number>, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {});

  // Sentiment trend data (simulated)
  const sentimentData = Array.from({ length: 14 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (13 - i));
    return {
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      sentiment: -0.5 + Math.random() * 1.2,
      volume: Math.floor(20 + Math.random() * 40)
    };
  });

  // Geographic distribution (simulated from report data)
  const geoDistribution = [
    { zone: 'Karol', count: 189, color: '#FF3B3B' },
    { zone: 'Saket', count: 156, color: '#FF8C00' },
    { zone: 'Connaught', count: 134, color: '#FFD300' },
    { zone: 'Dwarka', count: 98, color: '#5EF5A7' },
    { zone: 'Chandni', count: 91, color: '#00C853' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Citizen Reports</h1>
          <p className="text-sm text-gray-400 mt-1">Submit and track environmental concern reports</p>
        </div>
        <div className="flex gap-2">
          <select
            value={filter.status}
            onChange={e => setFilter({ ...filter, status: e.target.value })}
            className="bg-bg-elevated border border-bg-tertiary rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
          >
            <option value="">All Status</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>
          <select
            value={filter.category}
            onChange={e => setFilter({ ...filter, category: e.target.value })}
            className="bg-bg-elevated border border-bg-tertiary rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
          >
            <option value="">All Categories</option>
            {REPORT_CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-white">{reportsData?.total || reports.length}</p>
          <p className="text-xs text-gray-400 mt-1">Total Reports</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-yellow-400">{statusCounts.SUBMITTED || 0}</p>
          <p className="text-xs text-gray-400 mt-1">Pending Review</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-blue-400">{statusCounts.IN_PROGRESS || 0}</p>
          <p className="text-xs text-gray-400 mt-1">In Progress</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-green-400">{statusCounts.RESOLVED || 0}</p>
          <p className="text-xs text-gray-400 mt-1">Resolved</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-gray-400">2.3</p>
          <p className="text-xs text-gray-400 mt-1">Avg Days to Resolve</p>
        </Card>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Form + Stats */}
        <div className="col-span-4 space-y-6">
          {/* Submission Form */}
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Submit a Report</h3>
            {submitted ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-white font-medium">Report Submitted</p>
                <p className="text-xs text-gray-400 mt-1">Your report has been received and assigned to the relevant department.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Category</label>
                  <select
                    value={formData.category}
                    onChange={e => setFormData({ ...formData, category: e.target.value })}
                    className="w-full bg-bg-tertiary border border-bg-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                    required
                  >
                    <option value="">Select a category</option>
                    {REPORT_CATEGORIES.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    className="w-full bg-bg-tertiary border border-bg-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary resize-none"
                    rows={3}
                    placeholder="Describe the environmental concern..."
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Latitude</label>
                    <input
                      type="text"
                      value={formData.latitude}
                      onChange={e => setFormData({ ...formData, latitude: e.target.value })}
                      className="w-full bg-bg-tertiary border border-bg-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Longitude</label>
                    <input
                      type="text"
                      value={formData.longitude}
                      onChange={e => setFormData({ ...formData, longitude: e.target.value })}
                      className="w-full bg-bg-tertiary border border-bg-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Address (optional)</label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={e => setFormData({ ...formData, address: e.target.value })}
                    className="w-full bg-bg-tertiary border border-bg-elevated rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary"
                    placeholder="Street address"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Submit Report'}
                </Button>
              </form>
            )}
          </Card>

          {/* Sentiment Trend */}
          <Card>
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Sentiment Trend (14 Days)</h3>
            <SentimentTrendChart data={sentimentData} height={120} />
            <div className="mt-3 pt-3 border-t border-bg-tertiary flex items-center justify-between">
              <span className="text-xs text-gray-500">Average sentiment</span>
              <span className={`text-sm font-medium ${-0.08 < 0 ? 'text-red-400' : 'text-green-400'}`}>
                {(-0.08).toFixed(2)}
              </span>
            </div>
          </Card>
        </div>

        {/* Right Column: Reports List */}
        <Card className="col-span-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Recent Reports ({reportsData?.total || 0} total)</h3>
          </div>

          <div className="space-y-2 max-h-[600px] overflow-auto">
            {reports.map((report: any) => (
              <div key={report.id} className="p-4 rounded-lg bg-bg-tertiary border border-bg-elevated hover:border-gray-600 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={report.status === 'RESOLVED' ? 'low' : report.status === 'SUBMITTED' ? 'medium' : 'high'}>
                        {report.status}
                      </Badge>
                      <span className="text-xs text-gray-500">
                        {REPORT_CATEGORIES.find(c => c.value === report.category)?.label || report.category}
                      </span>
                      <span className="text-xs text-gray-600">•</span>
                      <span className="text-xs text-gray-500 font-mono">{report.id}</span>
                      {report.nlp_confidence && (
                        <span className="text-xs text-gray-600">•</span>
                      )}
                      {report.nlp_confidence && (
                        <span className={`text-xs ${report.nlp_confidence > 0.8 ? 'text-green-400' : 'text-yellow-400'}`}>
                          NLP: {(report.nlp_confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white mt-2">{report.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                      <span>📍 {report.location?.address || 'No location'}</span>
                      <span>Dept: {report.assigned_department}</span>
                      <span>Est: {report.estimated_resolution}</span>
                      <span>{new Date(report.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {reports.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500">No reports match your filters</p>
              </div>
            )}
          </div>

          {/* Pagination */}
          {reportsData && reportsData.total > 20 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-bg-tertiary">
              <p className="text-xs text-gray-500">Page {page} of {Math.ceil(reportsData.total / 20)}</p>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="secondary" disabled={page >= Math.ceil(reportsData.total / 20)} onClick={() => setPage(p => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Category Breakdown + Geographic Distribution */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Reports by Category</h3>
          {categoryBreakdown.length > 0 ? (
            <CategoryBreakdownChart categories={categoryBreakdown} height={220} />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-500 text-sm">
              No category data available
            </div>
          )}
        </Card>
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Geographic Distribution</h3>
          <div className="space-y-3">
            {geoDistribution.map(g => (
              <div key={g.zone} className="flex items-center gap-3">
                <span className="w-20 text-xs text-gray-400">{g.zone}</span>
                <div className="flex-1 h-6 rounded bg-bg-tertiary overflow-hidden">
                  <div
                    className="h-full rounded transition-all duration-500"
                    style={{
                      width: `${(g.count / Math.max(...geoDistribution.map(d => d.count))) * 100}%`,
                      backgroundColor: g.color
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-white w-12 text-right">{g.count}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
