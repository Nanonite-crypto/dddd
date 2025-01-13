const express = require('express');
const fetch = require('node-fetch');
const app = express();

app.use(async (req, res, next) => {
  const clientIp = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
  console.log("Client IP:", clientIp);

  // Discord Webhook URL
  const webhookUrl = 'YOUR_DISCORD_WEBHOOK_URL_HERE';

  // Prepare the message to send to Discord
  const message = {
    content: `Client IP: ${clientIp}`
  };

  try {
    // Send the message to Discord
    await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    });
  } catch (error) {
    console.error('Error sending message to Discord:', error);
  }

  next(); // Don't forget to call next() to continue the middleware chain
});

// Your other routes go here

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
