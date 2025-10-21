import sqlite3

conn = sqlite3.connect('clinic_scheduler.db')
cursor = conn.cursor()

# Check assignments with patient data
cursor.execute("SELECT COUNT(*) FROM schedule_assignments WHERE patient_id IS NOT NULL AND patient_id != ''")
count_with_patient_id = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM schedule_assignments WHERE patient_name IS NOT NULL AND patient_name != ''")
count_with_patient_name = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM schedule_assignments WHERE patient_id IS NOT NULL AND patient_id != '' AND patient_name IS NOT NULL AND patient_name != ''")
count_with_both = cursor.fetchone()[0]

print(f'Assignments with patient_id: {count_with_patient_id}')
print(f'Assignments with patient_name: {count_with_patient_name}')
print(f'Assignments with both patient_id and patient_name: {count_with_both}')

# Show a sample of assignments with patient data
cursor.execute("SELECT id, patient_id, patient_name, operation_id FROM schedule_assignments WHERE patient_id IS NOT NULL AND patient_id != '' LIMIT 5")
samples = cursor.fetchall()
print('Sample assignments with patient data:')
for sample in samples:
    print(f'  ID: {sample[0]}, Patient ID: {sample[1]}, Patient Name: {sample[2]}, Operation ID: {sample[3]}')

# Show total assignments
cursor.execute("SELECT COUNT(*) FROM schedule_assignments")
total = cursor.fetchone()[0]
print(f'Total assignments: {total}')

conn.close()

