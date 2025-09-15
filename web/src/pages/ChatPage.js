import React, { useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  Box,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Paper,
} from '@mui/material';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');

  const getActiveBot = (message) => {
    const keywords = ['new project', 'application', 'tech spec', 'technical specification'];
    const lowerCaseMessage = message.toLowerCase();
    for (const keyword of keywords) {
      if (lowerCaseMessage.includes(keyword)) {
        return 'A';
      }
    }
    return 'B';
  };

  // TODO: A more sophisticated routing logic should be implemented in a dedicated backend service (BFF).
  // This could involve using a more advanced NLP model to classify the user's intent and route the query
  // to the appropriate chatbot. For now, we are using a simple keyword-based approach.
  const handleSendMessage = async () => {
    if (inputValue.trim() === '') return;

    const userMessage = { sender: 'user', text: inputValue };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInputValue('');

    const activeBot = getActiveBot(inputValue);

    try {
      let response;
      if (activeBot === 'A') {
        const chatHistory = messages.map(msg => ({
          sender: msg.sender,
          text: msg.text,
        }));
        chatHistory.push(userMessage);
        response = await axios.post(`${process.env.REACT_APP_CHATBOT_A_URL}/api/chat`, {
          messages: chatHistory,
        });
      } else {
        response = await axios.post(`${process.env.REACT_APP_CHATBOT_B_URL}/ask`, {
          query: inputValue,
        });
      }

      const botMessage = { sender: 'bot', text: response.data.answer || response.data.reply };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        sender: 'bot',
        text: 'Sorry, I am having trouble connecting to the server. Please try again later.',
      };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    }
  };

  return (
    <Container>
      <Typography variant="h2" component="h1" gutterBottom>
        Chat
      </Typography>
      <Paper
        elevation={3}
        sx={{ height: '60vh', display: 'flex', flexDirection: 'column' }}
      >
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
          <List>
            {messages.map((message, index) => (
              <ListItem key={index}>
                <ListItemText
                  primary={message.text}
                  secondary={message.sender}
                  sx={{
                    textAlign: message.sender === 'user' ? 'right' : 'left',
                  }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
        <Box sx={{ p: 2, display: 'flex' }}>
          <TextField
            fullWidth
            variant="outlined"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleSendMessage();
              }
            }}
          />
          <Button
            variant="contained"
            color="primary"
            onClick={handleSendMessage}
            sx={{ ml: 2 }}
          >
            Send
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default ChatPage;
