import sqlite3

conn = sqlite3.connect('./clinic_scheduler.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Available tables:')
for table in tables:
    print(f'  {table[0]}')

# Check student table structure
try:
    cursor.execute("PRAGMA table_info(student_schedule_students)")
    columns = cursor.fetchall()
    print('\nStudentSchedule table columns:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')
except:
    print('\nStudentSchedule table not found')

# Check pairs table structure
try:
    cursor.execute("PRAGMA table_info(student_pairs)")
    columns = cursor.fetchall()
    print('\nStudentPairs table columns:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')
except:
    print('\nStudentPairs table not found')

# Check actual student data
try:
    cursor.execute('SELECT student_id, first_name, last_name, grade_level FROM student_schedule_students LIMIT 3')
    students = cursor.fetchall()
    print('\nSample student data:')
    for student in students:
        print(f'  {student[0]}: {student[1]} {student[2]} - Grade {student[3]}')
except Exception as e:
    print(f'\nError getting student data: {e}')

# Check actual pairs data
try:
    cursor.execute('SELECT id, pair_id, student1_id, student2_id FROM student_pairs LIMIT 3')
    pairs = cursor.fetchall()
    print('\nSample pair data:')
    for pair in pairs:
        print(f'  {pair[1]}: Student1={pair[2]}, Student2={pair[3]}')
except Exception as e:
    print(f'\nError getting pairs data: {e}')

conn.close()
