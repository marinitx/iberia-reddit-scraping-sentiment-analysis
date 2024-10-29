import praw
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import time
from prawcore.exceptions import RequestException
from requests.exceptions import Timeout

def setup_reddit():
    """Initialize Reddit API connection"""
    return praw.Reddit(
        client_id="YOUR API ID",
        client_secret="YOUR SECRET ID",
        user_agent="Opinion Mining Script by /u/YOUR USER",
        username="YOUR USER",
        password="YOUR PASSWORD",
        timeout=10
    )

def get_sentiment(text):
    """Calculate sentiment score for a piece of text"""
    try:
        analysis = TextBlob(text)
        return analysis.sentiment.polarity
    except:
        return 0

def clean_text(text):
    """Clean and prepare text for analysis"""
    if not isinstance(text, str):
        return ""
    return ' '.join(text.split()).strip()

def is_relevant(text, title=""):
    """Check if the content is relevant to Iberia airline"""
    text = text.lower()
    title = title.lower()
    
    airline_terms = [
        'flight', 'vuelo', 'airline', 'aerolínea', 'airport', 'aeropuerto',
        'delayed', 'retraso', 'cancelled', 'cancelado', 'booking', 'reserva',
        'madrid', 'barajas', 'spain', 'españa', 'maleta', 'luggage',
        'passenger', 'pasajero', 'ticket', 'billete'
    ]
    
    if 'iberia' not in text and 'iberia' not in title:
        return False
        
    return any(term in text or term in title for term in airline_terms)

def analyze_iberia():
    reddit = setup_reddit()
    data = []
    
    search_terms = [
        '"iberia" airline',
        '"iberia" flight',
        '"iberia" vuelo',
        '"iberia" review',
        '"iberia" experience',
        '"iberia" opinión'
    ]
    
    print("Collecting posts and comments about iberia airline...")
    
    processed_submissions = set()
    
    for search_term in search_terms:
        try:
            print(f"\nBuscando: {search_term}")
            
            # Búsqueda en subreddits relevantes
            for subreddit in ['travel', 'flights', 'spain', 'europe']:
                try:
                    for submission in reddit.subreddit(subreddit).search(search_term, limit=10, sort='new'):
                        if submission.id in processed_submissions:
                            continue
                            
                        processed_submissions.add(submission.id)
                        
                        if not is_relevant(submission.selftext, submission.title):
                            continue
                            
                        try:
                            post_data = {
                                'type': 'post',
                                'subreddit': submission.subreddit.display_name,
                                'title': submission.title,
                                'text': clean_text(submission.selftext) if submission.selftext else clean_text(submission.title),
                                'score': submission.score,
                                'created_utc': datetime.fromtimestamp(submission.created_utc),
                                'url': f"https://reddit.com{submission.permalink}",
                                'num_comments': submission.num_comments
                            }
                            post_data['sentiment'] = get_sentiment(post_data['text'])
                            data.append(post_data)
                            print(f"Procesando post: {submission.title[:100]}...")
                            
                            # Procesar comentarios
                            try:
                                submission.comments.replace_more(limit=0)
                                for comment in submission.comments.list():
                                    if hasattr(comment, 'body') and is_relevant(comment.body):
                                        comment_data = {
                                            'type': 'comment',
                                            'subreddit': submission.subreddit.display_name,
                                            'text': clean_text(comment.body),
                                            'score': comment.score,
                                            'created_utc': datetime.fromtimestamp(comment.created_utc),
                                            'url': f"https://reddit.com{submission.permalink}{comment.id}",
                                            'num_comments': 0
                                        }
                                        comment_data['sentiment'] = get_sentiment(comment_data['text'])
                                        data.append(comment_data)
                            
                            except (RequestException, Timeout) as e:
                                print(f"Error procesando comentarios: {str(e)}")
                                continue
                            
                            time.sleep(2)
                            
                        except Exception as e:
                            print(f"Error procesando submission: {str(e)}")
                            continue
                            
                except Exception as e:
                    print(f"Error en subreddit {subreddit}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error en término de búsqueda {search_term}: {str(e)}")
            continue
    
    # Convertir a DataFrame
    df = pd.DataFrame(data)
    
    if len(df) > 0:
        print("\nResultados del análisis:")
        print(f"Total de menciones relevantes encontradas: {len(df)}")
        print(f"Puntuación promedio de sentimiento: {df['sentiment'].mean():.2f}")
        
        print("\nDesglose por tipo:")
        print(df.groupby('type')['sentiment'].agg(['count', 'mean']))
        
        print("\nDesglose por subreddit:")
        print(df.groupby('subreddit')['sentiment'].agg(['count', 'mean']))
        
        # Mostrar algunos ejemplos de posts más relevantes
        print("\nEjemplos de posts encontrados:")
        for _, row in df[df['type'] == 'post'].head(3).iterrows():
            print(f"\nTítulo: {row['title']}")
            print(f"Sentimiento: {row['sentiment']:.2f}")
            print(f"URL: {row['url']}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"iberia_analysis_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"\nResultados guardados en {filename}")
    else:
        print("No se encontraron menciones relevantes de iberia")
    
    return df

if __name__ == "__main__":
    try:
        df = analyze_iberia()
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")