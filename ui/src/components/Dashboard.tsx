import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Refresh,
  Security,
  Storage,
  Speed,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { format } from 'date-fns';

import { fetchDashboardData } from '../services/api';
import StatusCard from './StatusCard';
import PipelineChart from './PipelineChart';

interface DashboardData {
  pipelineStatus: {
    running: number;
    completed: number;
    failed: number;
    pending: number;
  };
  securityStatus: {
    encryptionActive: boolean;
    auditLogging: boolean;
    accessControls: boolean;
    lastSecurityScan: string;
  };
  performance: {
    avgProcessingTime: number;
    throughput: number;
    errorRate: number;
  };
  compliance: {
    hipaaCompliant: boolean;
    lastAudit: string;
    violations: number;
  };
  recentAlerts: Array<{
    id: string;
    severity: 'critical' | 'warning' | 'info';
    message: string;
    timestamp: string;
  }>;
}

const Dashboard: React.FC = () => {
  const { data, isLoading, error, refetch } = useQuery<DashboardData>(
    'dashboard',
    fetchDashboardData,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  const handleRefresh = () => {
    refetch();
  };

  if (isLoading) {
    return (
      <Box sx={{ width: '100%' }}>
        <LinearProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Typography color="error" variant="h6">
            Error loading dashboard data
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const { pipelineStatus, securityStatus, performance, compliance, recentAlerts } = data!;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          HIPAA ETL Pipeline Dashboard
        </Typography>
        <Tooltip title="Refresh data">
          <IconButton onClick={handleRefresh} size="large">
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Pipeline Status Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <StatusCard
            title="Running"
            value={pipelineStatus.running}
            icon={<Speed color="primary" />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatusCard
            title="Completed"
            value={pipelineStatus.completed}
            icon={<CheckCircle color="success" />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatusCard
            title="Failed"
            value={pipelineStatus.failed}
            icon={<Error color="error" />}
            color="error"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <StatusCard
            title="Pending"
            value={pipelineStatus.pending}
            icon={<Info color="warning" />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Pipeline Performance Chart */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Pipeline Performance
              </Typography>
              <PipelineChart />
            </CardContent>
          </Card>
        </Grid>

        {/* Security Status */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Security Status
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Security sx={{ mr: 1 }} />
                  <Typography variant="body2">Encryption</Typography>
                  <Chip
                    label={securityStatus.encryptionActive ? 'Active' : 'Inactive'}
                    color={securityStatus.encryptionActive ? 'success' : 'error'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Storage sx={{ mr: 1 }} />
                  <Typography variant="body2">Audit Logging</Typography>
                  <Chip
                    label={securityStatus.auditLogging ? 'Active' : 'Inactive'}
                    color={securityStatus.auditLogging ? 'success' : 'error'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Security sx={{ mr: 1 }} />
                  <Typography variant="body2">Access Controls</Typography>
                  <Chip
                    label={securityStatus.accessControls ? 'Active' : 'Inactive'}
                    color={securityStatus.accessControls ? 'success' : 'error'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
              </Box>
              <Typography variant="caption" color="text.secondary">
                Last Security Scan: {format(new Date(securityStatus.lastSecurityScan), 'MMM dd, yyyy HH:mm')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Average Processing Time
                </Typography>
                <Typography variant="h4" color="primary">
                  {performance.avgProcessingTime.toFixed(1)}s
                </Typography>
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Throughput (records/min)
                </Typography>
                <Typography variant="h4" color="primary">
                  {performance.throughput.toLocaleString()}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Error Rate
                </Typography>
                <Typography variant="h4" color={performance.errorRate > 0.05 ? 'error' : 'primary'}>
                  {(performance.errorRate * 100).toFixed(2)}%
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Compliance Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Status
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="body2">HIPAA Compliance</Typography>
                  <Chip
                    label={compliance.hipaaCompliant ? 'Compliant' : 'Non-Compliant'}
                    color={compliance.hipaaCompliant ? 'success' : 'error'}
                    size="small"
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Last Audit: {format(new Date(compliance.lastAudit), 'MMM dd, yyyy')}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Violations (Last 30 days)
                </Typography>
                <Typography variant="h4" color={compliance.violations > 0 ? 'error' : 'success'}>
                  {compliance.violations}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Alerts */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Alerts
              </Typography>
              {recentAlerts.length === 0 ? (
                <Typography color="text.secondary">No recent alerts</Typography>
              ) : (
                recentAlerts.map((alert) => (
                  <Box key={alert.id} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    {alert.severity === 'critical' && <Error color="error" sx={{ mr: 1 }} />}
                    {alert.severity === 'warning' && <Warning color="warning" sx={{ mr: 1 }} />}
                    {alert.severity === 'info' && <Info color="info" sx={{ mr: 1 }} />}
                    <Typography variant="body2" sx={{ flexGrow: 1 }}>
                      {alert.message}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {format(new Date(alert.timestamp), 'MMM dd HH:mm')}
                    </Typography>
                  </Box>
                ))
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 