import React from 'react';
import { AppBar, Toolbar, Typography, Button } from '@mui/material';
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Unified Web Platform
        </Typography>
        <Button color="inherit" component={Link} to="/">
          Home
        </Button>
        <Button color="inherit" component={Link} to="/chat">
          Chat
        </Button>
        <Button color="inherit" component={Link} to="/album">
          Album
        </Button>
        <Button color="inherit" component={Link} to="/analytics">
          Analytics
        </Button>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
