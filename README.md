# CNU Dental Clinic Scheduler

A comprehensive web-based scheduling system for dental clinic operations, built with FastAPI and modern web technologies.

## Features

### Role-Based Access Control
- **Admin**: Full system access, user management, file uploads
- **Faculty**: Schedule management, student oversight, reporting
- **Front Desk**: Schedule viewing, student information, basic operations
- **Student**: Personal schedule viewing only

### Core Functionality
- Student and pair management
- Schedule creation and assignment
- Operation tracking and reporting
- File upload and data import
- Real-time dashboard with statistics

## Technology Stack

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML templates with Jinja2, Bootstrap 5, HTMX
- **Authentication**: JWT tokens with role-based permissions
- **Styling**: Bootstrap 5 with custom CSS

## Quick Start

### 1. Install Dependencies

```bash
cd clinic_scheduler_backend
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python create_tables.py
python init_student_schedule.py
```

### 3. Start the Server

```bash
python run.py
```

The application will be available at: `http://localhost:8000`

### 4. Access the Application

1. Open your browser and go to `http://localhost:8000`
2. You'll be redirected to the login page
3. Use the demo admin account: `admin` / `admin123`
4. Or register a new user account

## Default Accounts

- **Admin**: `admin` / `admin123`
- **Test Student**: `student1` / `password123` (register first)
- **Test Faculty**: `faculty1` / `password123` (register first)

## Project Structure

```
clinic_scheduler_backend/
├── app/
│   ├── api/                 # API endpoints
│   ├── core/               # Authentication and security
│   ├── models/             # SQLAlchemy database models
│   ├── schemas/            # Pydantic schemas
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration settings
│   └── database.py         # Database connection
├── templates/              # HTML templates
├── static/                 # CSS, JS, and static assets
├── alembic/               # Database migrations
├── requirements.txt       # Python dependencies
└── run.py                 # Server startup script
```

## API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

## Web Interface

The application provides a modern web interface with:

### Login/Registration
- Secure authentication with JWT tokens
- Role-based user registration
- Session management with cookies

### Dashboard Views
- **Admin Dashboard**: System overview, file management, user administration
- **Staff Dashboard**: Schedule management, student oversight, reporting
- **Student Dashboard**: Personal schedule viewing, assignment details

### Features
- Responsive design with Bootstrap 5
- Real-time updates with HTMX
- Interactive tables and forms
- File upload and download capabilities
- Export functionality for schedules

## Database Models

### Core Models
- **User**: Authentication and role management
- **StudentSchedule**: Student information and assignments
- **StudentPair**: Student pairing for clinic operations
- **ScheduleAssignment**: Individual time slot assignments
- **OperationSchedule**: Available dental operations
- **ScheduleWeekSchedule**: Weekly schedule organization

## Development

### Adding New Features

1. **Database Changes**: Update models in `app/models/`
2. **API Endpoints**: Add routes in `app/api/`
3. **Frontend**: Update templates in `templates/`
4. **Styling**: Modify CSS in `static/css/`

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

### Environment Configuration

Create a `.env` file for environment-specific settings:

```env
DATABASE_URL=sqlite:///./clinic_scheduler.db
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Production Deployment

### Database
- Switch to PostgreSQL for production
- Update `DATABASE_URL` in configuration
- Run migrations: `alembic upgrade head`

### Security
- Change the default `SECRET_KEY`
- Configure proper CORS settings
- Use HTTPS in production
- Set up proper user authentication

### Server
- Use a production ASGI server like Gunicorn
- Configure reverse proxy (nginx)
- Set up SSL certificates
- Configure logging and monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team or create an issue in the repository.