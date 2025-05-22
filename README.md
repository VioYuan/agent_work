# AI-Powered Chatbot System

An intelligent chatbot system that uses LangChain and OpenAI to provide personalized conversations based on user profiles and social media analysis.

## Features

- User profile management with social media integration
- Personalized chat responses based on user context
- Conversation quality metrics and satisfaction assessment
- Social media content analysis
- User management dashboard

## Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-chatbot-system.git
cd ai-chatbot-system
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Follow the on-screen instructions to:
   - Set up your user profile
   - Add social media links
   - Start chatting with the AI assistant

## Project Structure

```
ai-chatbot-system/
├── agents/
│   ├── base_agent.py
│   ├── chatbot_agent.py
│   ├── management_agent.py
│   └── user_agent.py
├── app.py
├── database.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- LangChain for the AI framework
- OpenAI for the language model
- Streamlit for the web interface 