# LinkedIn Publishing

Publish AI-generated posts to LinkedIn with proper formatting.

## LinkedIn API Setup

```python
# linkedin/publisher.py
import logging
from typing import Dict, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class LinkedInPublisher:
    """Publish posts to LinkedIn"""
    
    API_BASE = "https://api.linkedin.com/v2"
    
    def __init__(self, config: Dict):
        self.config = config
        self.access_token = config.get('linkedin_access_token')
        self.profile_id = config.get('linkedin_profile_id')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        })
    
    def create_post(self, post_text: str, url: Optional[str] = None) -> Dict:
        """Create a LinkedIn post"""
        
        # Prepare post content
        content = {
            'author': f'urn:li:person:{self.profile_id}',
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': post_text
                    },
                    'shareMediaCategory': 'ARTICLE' if url else 'NONE',
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }
        
        # Add URL if provided
        if url:
            content['specificContent']['com.linkedin.ugc.ShareContent']['media'] = [{
                'status': 'READY',
                'originalUrl': url
            }]
        
        try:
            response = self.session.post(
                f'{self.API_BASE}/ugcPosts',
                json=content
            )
            
            response.raise_for_status()
            
            post_id = response.headers.get('X-Restli-Id')
            
            return {
                'success': True,
                'post_id': post_id,
                'url': f'https://www.linkedin.com/feed/update/{post_id}'
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"LinkedIn API error: {e.response.text}")
            return {
                'success': False,
                'error': e.response.text
            }
        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_image_post(self, post_text: str, image_url: str) -> Dict:
        """Create a LinkedIn post with image"""
        
        # First, upload image
        asset_id = self._upload_image(image_url)
        
        if not asset_id:
            return {'success': False, 'error': 'Image upload failed'}
        
        content = {
            'author': f'urn:li:person:{self.profile_id}',
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': post_text
                    },
                    'shareMediaCategory': 'IMAGE',
                    'media': [{
                        'status': 'READY',
                        'media': asset_id
                    }]
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }
        
        try:
            response = self.session.post(
                f'{self.API_BASE}/ugcPosts',
                json=content
            )
            
            response.raise_for_status()
            
            return {
                'success': True,
                'post_id': response.headers.get('X-Restli-Id')
            }
            
        except Exception as e:
            logger.error(f"Error creating image post: {e}")
            return {'success': False, 'error': str(e)}
    
    def _upload_image(self, image_url: str) -> Optional[str]:
        """Upload image to LinkedIn"""
        
        # Register upload
        register_response = self.session.post(
            f'{self.API_BASE}/assets',
            json={
                'registerUploadRequest': {
                    'recipes': ['urn:li:digitalmediaRecipe:feedshare-image'],
                    'owner': f'urn:li:person:{self.profile_id}',
                    'serviceRelationships': [{
                        'relationshipType': 'OWNER',
                        'identifier': 'urn:li:userGeneratedContent'
                    }]
                }
            }
        )
        
        if register_response.status_code != 200:
            return None
        
        data = register_response.json()
        asset_id = data['value']['asset']
        upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        
        # Upload image
        image_response = requests.put(
            upload_url,
            data=requests.get(image_url).content,
            headers={'Content-Type': 'image/jpeg'}
        )
        
        if image_response.status_code == 201 or image_response.status_code == 200:
            return asset_id
        
        return None
    
    def delete_post(self, post_id: str) -> bool:
        """Delete a LinkedIn post"""
        
        try:
            response = self.session.delete(
                f'{self.API_BASE}/ugcPosts/{post_id}'
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False
    
    def get_post_stats(self, post_id: str) -> Dict:
        """Get statistics for a post"""
        
        try:
            response = self.session.get(
                f'{self.API_BASE}/ugcPosts/{post_id}'
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'likes': data.get('totalLikes', 0),
                'comments': data.get('totalComments', 0),
                'shares': data.get('totalShares', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
```

## OAuth Authentication

```python
# linkedin/auth.py
import webbrowser
from typing import Tuple
import requests

class LinkedInAuth:
    """Handle LinkedIn OAuth"""
    
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    REDIRECT_URI = "http://localhost:8080/callback"
    SCOPE = "r_liteprofile r_emailaddress w_member_social"
    
    AUTH_URL = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    def get_auth_url(self) -> str:
        """Get authorization URL"""
        return self.AUTH_URL
    
    def get_access_token(self, code: str) -> Tuple[bool, str]:
        """Exchange code for access token"""
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.REDIRECT_URI,
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        
        if response.status_code == 200:
            return True, response.json()['access_token']
        
        return False, ""
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, str]:
        """Refresh access token"""
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        
        if response.status_code == 200:
            return True, response.json()['access_token']
        
        return False, ""
```

## Post Queue

```python
# linkedin/queue.py
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class PostQueue:
    """Manage LinkedIn post queue"""
    
    def __init__(self, queue_file: str = 'data/post_queue.json'):
        self.queue_file = queue_file
        Path(queue_file).parent.mkdir(parents=True, exist_ok=True)
        self.queue = self._load_queue()
    
    def _load_queue(self) -> list:
        """Load queue from file"""
        if Path(self.queue_file).exists():
            with open(self.queue_file) as f:
                return json.load(f)
        return []
    
    def _save_queue(self):
        """Save queue to file"""
        with open(self.queue_file, 'w') as f:
            json.dump(self.queue, f, indent=2)
    
    def add_post(self, post: dict):
        """Add post to queue"""
        post['added_at'] = datetime.now().isoformat()
        post['status'] = 'pending'
        self.queue.append(post)
        self._save_queue()
    
    def get_pending(self) -> list:
        """Get pending posts"""
        return [p for p in self.queue if p['status'] == 'pending']
    
    def mark_posted(self, post_id: int, linkedin_post_id: str):
        """Mark post as published"""
        for post in self.queue:
            if post.get('id') == post_id:
                post['status'] = 'posted'
                post['posted_at'] = datetime.now().isoformat()
                post['linkedin_post_id'] = linkedin_post_id
        self._save_queue()
    
    def get_posted_today(self) -> int:
        """Get count of posts today"""
        today = datetime.now().date()
        
        count = 0
        for post in self.queue:
            if post['status'] == 'posted':
                posted_date = datetime.fromisoformat(post['posted_at']).date()
                if posted_date == today:
                    count += 1
        
        return count
    
    def can_post(self, max_per_day: int = 3) -> bool:
        """Check if can post today"""
        return self.get_posted_today() < max_per_day
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            'total': len(self.queue),
            'pending': len(self.get_pending()),
            'posted_today': self.get_posted_today(),
            'total_posted': len([p for p in self.queue if p['status'] == 'posted'])
        }
```

## Usage

```python
# main.py - LinkedIn publishing
from linkedin.publisher import LinkedInPublisher
from linkedin.queue import PostQueue

config = {
    'linkedin_access_token': 'your_token',
    'linkedin_profile_id': 'your_profile_id'
}

# Initialize
publisher = LinkedInPublisher(config)
queue = PostQueue()

# Check if can post
if queue.can_post():
    # Load processed job
    with open('data/jobs_processed.json') as f:
        jobs = json.load(f)
    
    if jobs:
        job = jobs[0]
        post_text = job.get('linkedin_post', '')
        
        # Create post
        result = publisher.create_post(post_text, job.get('url'))
        
        if result['success']:
            queue.mark_posted(job['id'], result['post_id'])
            print(f"Posted successfully: {result['url']}")
        else:
            print(f"Failed: {result['error']}")
else:
    print("Daily limit reached")
```

## Example Output

### LinkedIn Post Format

```
⚓ Yacht Job Opportunity! ⛵

🍳 Seeking an experienced Chef to join our team!

Position: Sous Chef
Location: Fort Lauderdale, FL
Salary: $75,000 - $85,000 + benefits

About the Role:
We're looking for a talented culinary professional to join our luxury superyacht team. You'll be responsible for creating exceptional dining experiences for our guests.

Requirements:
• 3+ years in high-end restaurants or yacht experience
• STCW certification preferred
• Strong Mediterranean & International cuisine skills

Benefits:
✨ Competitive salary
✨ Crew travel opportunities
✨ World-class working environment

👇 Apply now or DM for details!

#YachtJobs #Superyacht #MarineCareers #ChefJobs #LuxuryYacht #Boating #MarineIndustry #YachtChef #CulinaryCareers #Hiring
```

## Next Steps

Continue to Project 3: [Ebook Summarizer Overview](./11-ebook-summarizer-overview.md)
