# Email Agent - AI-Powered Email Processing System

An intelligent email agent system that automatically processes Gmail emails, generates AI-powered responses, and manages email workflows using FastAPI, OpenAI, and modern Python technologies.

## 🚀 Features

- **Gmail Integration**: Seamless integration with Gmail API for reading and sending emails
- **AI-Powered Processing**: Intelligent email analysis and response generation using OpenAI GPT models
- **Automated Scheduling**: Background task scheduling for continuous email monitoring
- **Knowledge Base**: Vector-based knowledge management for context-aware responses
- **RESTful API**: Comprehensive API endpoints for managing emails and system configuration
- **Priority Classification**: Automatic email priority detection and classification
- **Response Confidence**: AI confidence scoring for automated response decisions
- **Dashboard Analytics**: Real-time statistics and system monitoring

## 📋 Prerequisites

- Python 3.9+
- Gmail account with API access
- OpenAI API key
- Git

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd email_agent
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Gmail API Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./email_agent.db

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=true
LOG_LEVEL=INFO

# Email Processing Configuration
MAX_EMAILS_PER_BATCH=10
EMAIL_CHECK_INTERVAL=300  # seconds
AUTO_RESPOND_ENABLED=true

# AI Agent Configuration
DEFAULT_AI_MODEL=gpt-4
MAX_RESPONSE_LENGTH=500
TEMPERATURE=0.7
```

### 5. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials JSON file and save it as `credentials.json` in the project root

### 6. Database Initialization
```bash
python -c "
import asyncio
from app.db.database import init_db
asyncio.run(init_db())
"
```

## 🚀 Usage

### Start the Application
```bash
# Development mode
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Access the API
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/status

## 📚 API Endpoints

### Email Management
- `GET /emails/` - List emails with filtering
- `GET /emails/{email_id}` - Get specific email details
- `POST /emails/sync` - Manually trigger email synchronization
- `POST /emails/{email_id}/generate-response` - Generate AI response
- `POST /emails/{email_id}/send-response/{response_id}` - Send generated response
- `PUT /emails/{email_id}/status` - Update email status
- `PUT /emails/{email_id}/priority` - Update email priority
- `GET /emails/stats/dashboard` - Get dashboard statistics

### Knowledge Base
- `POST /knowledge/` - Create knowledge base entry
- `GET /knowledge/` - List knowledge base entries
- `GET /knowledge/{entry_id}` - Get specific knowledge entry
- `PUT /knowledge/{entry_id}` - Update knowledge entry
- `DELETE /knowledge/{entry_id}` - Delete knowledge entry
- `POST /knowledge/search` - Search knowledge base
- `POST /knowledge/upload` - Upload files to knowledge base
- `GET /knowledge/stats/overview` - Get knowledge base statistics

## 🔧 Configuration

### Email Processing Settings
- `EMAIL_CHECK_INTERVAL`: How often to check for new emails (seconds)
- `MAX_EMAILS_PER_BATCH`: Maximum emails to process in one batch
- `AUTO_RESPOND_ENABLED`: Enable/disable automatic responses

### AI Configuration
- `DEFAULT_AI_MODEL`: OpenAI model to use (gpt-4, gpt-3.5-turbo)
- `MAX_RESPONSE_LENGTH`: Maximum response length in words
- `TEMPERATURE`: AI response creativity (0.0-1.0)

### Database Configuration
- `DATABASE_URL`: SQLite database connection string
- Supports async SQLite with aiosqlite

## 🏗️ Architecture

### Core Components
1. **FastAPI Application** (`app/main.py`): Main application and API endpoints
2. **Database Models** (`app/db/models.py`): SQLModel-based data models
3. **Gmail Client** (`app/mail/gmail_client.py`): Gmail API integration
4. **AI Agent** (`app/agent/ai_agent.py`): OpenAI-powered email processing
5. **Knowledge Base** (`app/agent/knowledge_base.py`): FAISS-based vector storage
6. **Scheduler** (`app/agent/scheduler.py`): Background task automation

### Data Flow
1. **Email Ingestion**: Scheduler fetches new emails from Gmail
2. **AI Processing**: Emails are analyzed for priority and content
3. **Response Generation**: AI generates contextual responses
4. **Confidence Scoring**: System evaluates response quality
5. **Automated Sending**: High-confidence responses are sent automatically
6. **Knowledge Learning**: Successful interactions are stored for future use

## 🧪 Testing

### Run Tests
```bash
pytest tests/ -v
```

### Test Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## 📊 Monitoring

### System Health
- Monitor `/health` endpoint for system status
- Check `/status` endpoint for detailed system information
- Review logs for processing statistics

### Performance Metrics
- Email processing throughput
- Response generation accuracy
- Knowledge base search performance
- API response times

## 🔒 Security

### Best Practices
1. **Environment Variables**: Never commit sensitive data
2. **API Keys**: Secure storage of OpenAI and Google credentials
3. **CORS Configuration**: Restrict origins in production
4. **Rate Limiting**: Implement API rate limiting for production
5. **Input Validation**: All inputs are validated and sanitized

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t email-agent .

# Run container
docker run -p 8000:8000 --env-file .env email-agent
```

### Production Considerations
1. **Database**: Use PostgreSQL for production
2. **Reverse Proxy**: Use Nginx or similar
3. **SSL/TLS**: Enable HTTPS
4. **Monitoring**: Set up logging and monitoring
5. **Backup**: Regular database backups

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the [documentation](http://localhost:8000/docs)
2. Review existing issues
3. Create a new issue with detailed information

## 🔮 Future Enhancements

- **Multi-account Support**: Handle multiple Gmail accounts
- **Advanced AI Models**: Support for custom fine-tuned models
- **Email Templates**: Customizable response templates
- **Integration APIs**: Webhook support for external systems
- **Mobile App**: Native mobile application
- **Advanced Analytics**: Machine learning insights and recommendations