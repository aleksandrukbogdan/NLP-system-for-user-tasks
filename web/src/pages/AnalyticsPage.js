import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Grid,
  Card,
  CardContent,
} from '@mui/material';

const AnalyticsPage = () => {
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${process.env.REACT_APP_CHATBOT_A_URL}/api/analytics`)
      .then((response) => {
        setAnalytics(response.data.data);
      })
      .catch((err) => {
        setError('Failed to fetch analytics data.');
        console.error(err);
      });
  }, []);

  if (error) {
    return <Container><Typography color="error">{error}</Typography></Container>;
  }

  if (!analytics) {
    return <Container>Loading...</Container>;
  }

  return (
    <Container>
      <Typography variant="h2" component="h1" gutterBottom>
        Task Analytics
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={6}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Tasks
              </Typography>
              <Typography variant="h5" component="h2">
                {analytics.total_tasks}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg. Messages per Task
              </Typography>
              <Typography variant="h5" component="h2">
                {analytics.avg_messages_per_task}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Typography variant="h4" component="h2" gutterBottom>
        Tasks per Day
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell align="right">Task Count</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(analytics.tasks_per_day).map(([day, count]) => (
              <TableRow key={day}>
                <TableCell component="th" scope="row">
                  {day}
                </TableCell>
                <TableCell align="right">{count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
};

export default AnalyticsPage;
