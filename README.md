Multiplayer Chess Game with Real-Time WebSockets
Course Project | CSCI 620 - Web Technology

Overview
This project is a real-time multiplayer chess game developed using Django, Django Channels, and WebSockets. 
It evolved from an earlier AJAX-polling implementation (Project 2) to leverage WebSockets for instant gameplay updates, reducing latency and server load. 


Key features include:

1)Real-time move validation and synchronization using the python-chess library.
2)User presence tracking (online/offline status) and challenge notifications.
3)Scalable architecture with Redis as a message broker and deployment on Google Cloud Platform (GCP).

Technologies
Backend: Django, Django Channels, Redis

Frontend: Server-side rendering (SSR) with WebSocket integration

Deployment: Docker, GCP Compute Engine

Libraries: python-chess (game logic), channels_redis (WebSocket scaling)

Key Improvements Over AJAX Polling
50% lower latency for move updates.

Reduced server load by eliminating periodic polling.

Seamless UX with instant feedback for moves, resignations, and player status.

Links
Demo Video (WebSockets): https://drive.google.com/file/d/1bXLHBVFLOJ2DF9InizlyWWw4tmex_OVL/view?usp=drive_link
