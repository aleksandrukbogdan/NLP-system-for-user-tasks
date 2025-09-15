import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
} from '@mui/material';

const AlbumPage = () => {
  const [solutions, setSolutions] = useState([]);

  useEffect(() => {
    axios.get('/solutions.json').then((response) => {
      setSolutions(response.data);
    });
  }, []);

  return (
    <Container>
      <Typography variant="h2" component="h1" gutterBottom>
        Standard Solutions Album
      </Typography>
      <Grid container spacing={4}>
        {solutions.map((solution) => (
          <Grid item key={solution.id} xs={12} sm={6} md={4}>
            <Card>
              <CardMedia
                component="img"
                height="140"
                image={solution.image}
                alt={solution.title}
              />
              <CardContent>
                <Typography gutterBottom variant="h5" component="div">
                  {solution.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {solution.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default AlbumPage;
