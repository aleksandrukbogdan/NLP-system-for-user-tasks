import React from 'react';
import { Container, Typography } from '@mui/material';

const HomePage = () => {
  return (
    <Container>
      <Typography variant="h2" component="h1" gutterBottom>
        Welcome to the Unified Web Platform
      </Typography>
      <Typography variant="body1">
        This platform integrates our department's services into a single, cohesive experience.
      </Typography>
    </Container>
  );
};

export default HomePage;
