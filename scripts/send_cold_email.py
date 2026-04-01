#!/usr/bin/env python3
"""Riley SDR - Cold Email Sender via Gmail API"""

import sqlite3
import subprocess
import time

DB_PATH = 'Owner Inbox/instance/owner_inbox.db'

def get_valid_prospects(limit=15):
    """Get valid prospect contacts from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = '''SELECT p.id, p.business_name, r.name, r.email, p.industry
                   FROM prospects p 
                   LEFT JOIN ro_contacts r ON p.id = r.prospect_id
                   WHERE status = 'new' AND r.email IS NOT NULL
                   AND r.email != '' AND r.email LIKE '%@%'
                   ORDER BY p.updated_at DESC LIMIT ?'''
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        conn.close()
        
        contacts = []
        for row in results:
            email = row[3].split(',')[0] if ',' in row[3] else row[3]
            if '@' in email and not email.startswith('http') and '.png' not in email.lower():
                contacts.append({
                    'id': row[0],
                    'company': row[1].replace('&', ' ').replace('\'', ''),
                    'name': row[2] or "Key Contact",
                    'email': email.strip(),
                    'industry': row[4]
                })
        return contacts
    except Exception as e:
        print(f"Database error: {e}")
        return []

def send_email(to_addr, subject, body):
    """Send via GWS CLI with positional args (no flags)"""
    cmd = ['uvx', 'gws-cli', 'gmail', 'send']
    
    # Positional arguments only: TO, SUBJECT, [BODY]
    cmd.extend([to_addr, subject])
    if body:
        cmd.append(body)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            return {
                'success': True,
                'to': to_addr,
                'subject': subject[:50],
                'msg_id': data.get('message_id', 'unknown')
            }
        except:
            return {
                'success': True,
                'to': to_addr,
                'subject': subject[:50],
                'msg_id': result.stdout.strip()
            }
    
    error = result.stderr[:100] if result.stderr else result.stdout[:100]
    return {
        'success': False,
        'error': f"Send failed: {error}"
    }

def compose_email(prospect):
    """Compose personalized email based on industry"""
    clean_name = prospect['company'].replace('&', '').replace('\'', '')[:30]
    
    if 'brewing' in prospect['industry'].lower() or 'brewery' in prospect['industry'].lower():
        subject = f"Local Gas Partner for Breweries Like {clean_name}"
        body = f"""Subject: Local Gas Partner for Breweries Like {clean_name}

{prospect['name']},

I noticed you operate in the brewery industry — consistent CO₂ supply is critical for draft systems and fermentation.

My company, Roberts Oxygen, specializes in bulk CO₂ systems specifically for breweries. We help establishments like {clean_name} reduce costs by 60-80% versus bottled CO₂.

Current brewery setups typically cost $8,000/year on bottled gas. A bulk storage system could save you that amount annually.

I'd love to show you how it works — available for a brief call today or tomorrow?

Best,
Riley SDR | Roberts Oxygen"""
        
    elif 'food' in prospect['industry'].lower() or 'processing' in prospect['industry'].lower():
        subject = f"Bulk Gas Solutions for {clean_name}"
        body = f"""Subject: Bulk Gas Solutions for {clean_name}

{prospect['name']},

Food processing facilities have strict temperature and gas purity requirements. Roberts Oxygen provides bulk CO₂, oxygen, and nitrogen systems for food processing. Our tanks are certified for food-grade applications.

For operations like {clean_name}, switching to bulk supply can reduce costs while ensuring consistent gas quality.

Would you be open to a brief discussion about your current gas setup?

Best,
Riley SDR | Roberts Oxygen"""
        
    else:
        subject = f"Local Gas Partner for {clean_name}"
        body = f"""Subject: Local Gas Partner for {clean_name}

{prospect['name']},

I'm reaching out from Roberts Oxygen, which supplies industrial gas to businesses in your area.

We help companies reduce gas costs by 60-80% through bulk storage systems versus traditional cylinder deliveries.

For a typical operation like {clean_name}, switching to bulk supply could save $5,000-$15,000 annually in fuel costs.

I'd love to show you how it works — would you be open to a brief 5-minute call this week?

Best,
Riley SDR | Roberts Oxygen"""
    
    return subject, body

def main():
    print("=== RILEY SDR - COLD OUTREACH BATCH ===\n")
    
    try:
        prospects = get_valid_prospects(limit=15)
    except Exception as e:
        print(f"Error: {e}\n")
        return
    
    if not prospects:
        print("⚠️  No valid contacts found\n")
        return
    
    sent_count = 0
    failed_count = 0
    
    for i, prospect in enumerate(prospects, 1):
        subject, body = compose_email(prospect)
        
        print(f"\n{i}. {prospect['company']}")
        print(f"   → {prospect['email']}")
        print(f"   Subject: {subject[:70]}...")
        
        result = send_email(prospect['email'], subject, body)
        
        if result.get('success'):
            sent_count += 1
            print(f"   ✅ SENT successfully (Msg ID: {result['msg_id']})")
        else:
            failed_count += 1
            print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
        
        time.sleep(2)  # Rate limiting
    
    print(f"\n{'='*70}")
    print(f"=== BATCH COMPLETE ===")
    print(f"✅ Emails Sent: {sent_count}")
    print(f"❌ Failed: {failed_count}")
    if sent_count + failed_count > 0:
        print(f"📊 Success Rate: {(sent_count/(sent_count+failed_count)*100):.1f}%")
    print("="*70)

if __name__ == '__main__':
    main()
