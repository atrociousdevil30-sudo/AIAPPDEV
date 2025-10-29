from flask import Blueprint, render_template, jsonify, request
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import random
import json
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    # Sample data - replace with actual data from your database
    resume_scores = [random.randint(60, 100) for _ in range(50)]
    
    # Enhanced metrics
    metrics = {
        'total_applicants': random.randint(100, 500),
        'shortlisted': random.randint(20, 100),
        'interviews': random.randint(10, 50),
        'hired': random.randint(1, 20),
        'avg_processing_time': f"{random.randint(1, 7)} days",
        'ats_score': random.randint(60, 95)
    }
    
    # Sentiment analysis data
    sentiment_data = {
        'Positive': random.randint(5, 15),
        'Neutral': random.randint(2, 10),
        'Negative': random.randint(1, 5)
    }
    
    # Generate hiring trends data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    date_range = pd.date_range(start_date, end_date, freq='W')
    trends_data = {
        'date': date_range,
        'applications': [random.randint(10, 50) for _ in date_range],
        'interviews': [random.randint(5, 25) for _ in date_range],
        'hires': [random.randint(1, 10) for _ in date_range],
        'rejections': [random.randint(5, 30) for _ in date_range]
    }
    
    # Skill distribution data
    skills = ['Python', 'JavaScript', 'Java', 'SQL', 'React', 'Node.js', 'AWS', 'Docker']
    skill_distribution = [random.randint(10, 100) for _ in skills]
    
    # Recent activities
    activities = [
        {'id': i, 'candidate': f"Candidate {i}", 'action': random.choice(['Applied', 'Screened', 'Interviewed', 'Hired']), 
         'time': (datetime.now() - timedelta(hours=random.randint(1, 24))).strftime('%H:%M')}
        for i in range(1, 6)
    ]
    
    # Pipeline stages
    pipeline = [
        {'stage': 'Applied', 'count': metrics['total_applicants'], 'color': '#4e73df'},
        {'stage': 'Screened', 'count': metrics['shortlisted'], 'color': '#36b9cc'},
        {'stage': 'Interview', 'count': metrics['interviews'], 'color': '#1cc88a'},
        {'stage': 'Offered', 'count': random.randint(5, 15), 'color': '#f6c23e'},
        {'stage': 'Hired', 'count': metrics['hired'], 'color': '#e74a3b'}
    ]
    
    # Generate top candidates data
    candidates = [
        {'name': 'John Doe', 'score': 92, 'status': 'Interview Scheduled', 'applied': (end_date - timedelta(days=5)).strftime('%Y-%m-%d')},
        {'name': 'Jane Smith', 'score': 88, 'status': 'Offer Sent', 'applied': (end_date - timedelta(days=10)).strftime('%Y-%m-%d')},
        {'name': 'Robert Johnson', 'score': 85, 'status': 'New Application', 'applied': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')},
        {'name': 'Emily Davis', 'score': 82, 'status': 'Interviewed', 'applied': (end_date - timedelta(days=7)).strftime('%Y-%m-%d')},
        {'name': 'Michael Brown', 'score': 79, 'status': 'Screening', 'applied': (end_date - timedelta(days=3)).strftime('%Y-%m-%d')},
    ]
    
    # Create visualizations
    resume_chart = create_resume_score_chart(resume_scores)
    sentiment_chart = create_sentiment_chart(sentiment_data)
    hiring_trends = create_hiring_trends_chart(trends_data)
    
    # Skill distribution chart
    skill_chart = create_skill_distribution_chart(skills, skill_distribution)
    
    # Pipeline chart
    pipeline_chart = create_pipeline_chart(pipeline)
    
    return render_template('dashboard.html',
                         metrics=metrics,
                         activities=activities,
                         pipeline=pipeline,
                         resume_chart=resume_chart,
                         sentiment_chart=sentiment_chart,
                         hiring_trends=hiring_trends,
                         skill_chart=skill_chart,
                         pipeline_chart=pipeline_chart,
                         candidates=candidates,
                         sentiment_data=sentiment_data)

def create_resume_score_chart(scores):
    # Create histogram of resume scores with dark theme
    fig = go.Figure()
    
    # Calculate score distribution
    hist, bin_edges = np.histogram(scores, bins=10, range=(0, 100))
    
    # Create custom bin labels
    bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)]
    
    # Add histogram trace with gradient colors
    colors = ['#4e73df' if x < max(hist) else '#1cc88a' for x in hist]
    
    # Set dark theme colors
    bg_color = '#1a1a1a'
    grid_color = '#2d2d2d'
    text_color = '#f8f9fa'
    
    fig.add_trace(go.Bar(
        x=bin_labels,
        y=hist,
        marker_color=colors,
        opacity=0.85,
        name='Candidates',
        hovertemplate='<b>%{x}%</b><br>Count: %{y}<extra></extra>',
        marker_line=dict(color='white', width=1),
        width=0.8
    ))
    
    # Add mean and median lines
    mean_score = np.mean(scores)
    median_score = np.median(scores)
    
    fig.add_vline(
        x=mean_score/10 - 0.5,  # Adjust position for categorical x-axis
        line_dash='dash',
        line_color='#e74a3b',
        annotation_text=f'Mean: {mean_score:.1f}',
        annotation_position='top right',
        annotation_font_size=12,
        annotation_bgcolor='rgba(255,255,255,0.9)'
    )
    
    fig.add_vline(
        x=median_score/10 - 0.5,  # Adjust position for categorical x-axis
        line_dash='dot',
        line_color='#36b9cc',
        annotation_text=f'Median: {median_score:.1f}',
        annotation_position='top left',
        annotation_font_size=12,
        annotation_bgcolor='rgba(255,255,255,0.9)'
    )
    
    # Add pass/fail threshold (e.g., 70%)
    threshold = 70
    fig.add_vline(
        x=threshold/10 - 0.5,  # Adjust position for categorical x-axis
        line_dash='dash',
        line_color='#1cc88a',
        annotation_text=f'Pass: {threshold}%',
        annotation_position='top',
        annotation_font_size=12,
        annotation_bgcolor='rgba(255,255,255,0.9)'
    )
    
    # Add pass/fail summary
    pass_count = sum(1 for s in scores if s >= threshold)
    fail_count = len(scores) - pass_count
    
    fig.add_annotation(
        x=0.5,
        y=0.95,
        xref='paper',
        yref='paper',
        text=f"Pass: {pass_count} | Fail: {fail_count}",
        showarrow=False,
        font=dict(size=12, color='#4e73df'),
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#e5e7eb',
        borderwidth=1,
        borderpad=4
    )
    
    # Update layout with modern styling
    fig.update_layout(
        title=dict(
            text='Resume Score Distribution',
            x=0.5,
            y=0.95,
            font=dict(size=16, family='Inter', color=text_color)
        ),
        xaxis=dict(
            title='Score Range',
            title_font=dict(size=12, family='Inter'),
            tickfont=dict(size=11, family='Inter'),
            gridcolor=grid_color,
            linecolor=grid_color,
            zerolinecolor=grid_color,
            linewidth=1,
            mirror=True
        ),
        yaxis=dict(
            title='Number of Candidates',
            title_font=dict(size=12, family='Inter'),
            tickfont=dict(size=11, family='Inter'),
            gridcolor=grid_color,
            linecolor=grid_color,
            zerolinecolor=grid_color,
            linewidth=1,
            mirror=True
        ),
        bargap=0.1,
        template='plotly_dark',
        margin=dict(l=50, r=20, t=60, b=50),
        showlegend=False,
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, family='Inter'),
        height=400
    )
    
    # Add custom hover template
    fig.update_traces(
        hovertemplate='<b>%{x}%</b><br>' +
                     'Candidates: %{y}' +
                     '<extra></extra>'
    )
    
    # Add configuration for the chart
    fig.update_layout(
        # Remove the download button as it's not supported with the current Plotly version
        # Users can use the built-in download options in the Plotly toolbar
        # (the camera icon in the modebar) to download the chart
        modebar={
            'orientation': 'v',
            'bgcolor': 'rgba(255, 255, 255, 0.7)',
            'color': '#7f7f7f',
            'activecolor': '#1f77b4'
        }
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d']
    })

def create_sentiment_chart(sentiment_data):
    # Create pie chart for sentiment analysis with dark theme
    labels = ['Positive', 'Neutral', 'Negative']
    values = [sentiment_data.get(label, 0) for label in labels]
    
    # Define colors and hover text
    colors = ['#1cc88a', '#f6c23e', '#e74a3b']
    hover_text = [f"{label}: {value}" for label, value in zip(labels, values)]
    
    # Theme variables
    bg_color = '#1a1a1a'
    text_color = '#f8f9fa'
    
    # Create donut chart with enhanced styling
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='inside',
        hoverinfo='label+value+percent',
        textfont=dict(size=14, family='Inter'),
        sort=False,
        direction='clockwise',
        rotation=90,
        texttemplate='%{label}<br>%{percent:.0%}',
        hoverlabel=dict(
            bgcolor='white',
            font_size=14,
            font_family='Inter'
        ),
        marker=dict(
            line=dict(color='#ffffff', width=2)
        )
    )])
    
    # Add center text with total count
    total = sum(values)
    fig.add_annotation(
        text=f"{total}<br>Total",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, family='Inter', color='#4e73df'),
        align='center'
    )
    
    # Update layout with modern styling
    fig.update_layout(
        title=dict(
            text='Candidate Sentiment Analysis',
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font=dict(size=16, family='Inter')
        ),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.1,
            xanchor='center',
            x=0.5,
            font=dict(size=12, family='Inter', color=text_color)
        ),
        margin=dict(l=10, r=10, t=60, b=50),
        height=320,
        template='plotly_dark',
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, family='Inter'),
        uniformtext=dict(
            minsize=12,
            mode='hide'
        )
    )
    
    # Add custom hover template
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>' +
                     'Count: %{value}<br>' +
                     'Percentage: %{percent:.1%}' +
                     '<extra></extra>'
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={
        'displayModeBar': False
    })

def create_skill_distribution_chart(skills, distribution):
    """Create a horizontal bar chart for skill distribution with dark theme."""
    # Set dark theme colors
    bg_color = '#1a1a1a'
    grid_color = '#2d2d2d'
    text_color = '#f8f9fa'
    
    # Sort skills by distribution for better visualization
    sorted_skills = [x for _, x in sorted(zip(distribution, skills), reverse=True)]
    sorted_dist = sorted(distribution, reverse=True)
    
    # Create a horizontal bar chart
    fig = go.Figure(go.Bar(
        x=sorted_dist,
        y=sorted_skills,
        orientation='h',
        marker_color='#4e73df',
        opacity=0.85,
        text=sorted_dist,
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>',
    ))
    
    # Update layout with dark theme
    fig.update_layout(
        title=dict(
            text='Top In-Demand Skills',
            x=0.5,
            y=0.95,
            font=dict(size=16, family='Inter', color=text_color)
        ),
        xaxis=dict(
            title='Number of Candidates',
            title_font=dict(size=12, family='Inter'),
            tickfont=dict(size=11, family='Inter'),
            gridcolor=grid_color,
            linecolor=grid_color,
            zerolinecolor=grid_color,
            showgrid=True,
            showline=True,
            linewidth=1,
            mirror=True
        ),
        yaxis=dict(
            title='',
            tickfont=dict(size=11, family='Inter'),
            showgrid=False,
            showline=False,
            automargin=True
        ),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, family='Inter'),
        margin=dict(l=10, r=10, t=80, b=30, pad=5),
        height=400,
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.9)',
            font_size=12,
            font_family='Inter',
            font_color='#1a1a1a'
        )
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

def create_pipeline_chart(pipeline_data):
    """Create a funnel chart for recruitment pipeline with dark theme."""
    # Set dark theme colors
    bg_color = '#1a1a1a'
    text_color = '#f8f9fa'
    
    # Extract data from pipeline
    stages = [stage['stage'] for stage in pipeline_data]
    counts = [stage['count'] for stage in pipeline_data]
    colors = [stage['color'] for stage in pipeline_data]
    
    # Calculate conversion rates
    total = counts[0] if counts else 0
    conversion_rates = [f"{count} ({(count/total*100):.1f}%)" for count in counts]
    
    # Create funnel chart
    fig = go.Figure()
    
    fig.add_trace(go.Funnel(
        name='',
        y=stages,
        x=counts,
        textposition='inside',
        textinfo='value+percent initial',
        opacity=0.8,
        marker=dict(color=colors),
        connector=dict(line=dict(color='#6c757d', width=1)),
        textfont=dict(family='Inter', size=12, color='white')
    ))
    
    # Update layout with dark theme
    fig.update_layout(
        title=dict(
            text='Recruitment Pipeline',
            x=0.5,
            y=0.95,
            font=dict(size=16, family='Inter', color=text_color)
        ),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=text_color, family='Inter'),
        margin=dict(l=10, r=10, t=80, b=30, pad=5),
        height=400,
        hoverlabel=dict(
            bgcolor='rgba(255, 255, 255, 0.9)',
            font_size=12,
            font_family='Inter',
            font_color='#1a1a1a'
        ),
        showlegend=False
    )
    
    # Add annotations for conversion rates
    for i, (stage, rate) in enumerate(zip(stages, conversion_rates)):
        fig.add_annotation(
            x=0.95,
            y=1 - (i * 0.2),  # Position annotations to the right of the funnel
            xref='paper',
            yref='paper',
            text=f"{stage}: {rate}",
            showarrow=False,
            font=dict(size=12, color=text_color),
            xanchor='left'
        )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

def create_hiring_trends_chart(trends_data):
    # Create line chart for hiring trends with dark theme
    df = pd.DataFrame(trends_data)
    
    # Set dark theme colors
    bg_color = '#1a1a1a'
    grid_color = '#2d2d2d'
    text_color = '#f8f9fa'
    
    fig = go.Figure()
    
    # Add traces with more visible styling
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['applications'],
        mode='lines+markers',
        name='Applications',
        line=dict(color='#4e73df', width=3),
        marker=dict(size=8, symbol='circle')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['interviews'],
        mode='lines+markers',
        name='Interviews',
        line=dict(color='#1cc88a', width=3, dash='dash'),
        marker=dict(size=8, symbol='diamond')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['hires'],
        mode='lines+markers',
        name='Hires',
        line=dict(color='#36b9cc', width=3, dash='dot'),
        marker=dict(size=10, symbol='star')
    ))
    
    # Add rejection rate as a line chart if rejections data is available
    if 'rejections' in df.columns:
        rejection_rate = [r/(a+0.001)*100 for a, r in zip(df['applications'], df['rejections'])]
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=rejection_rate,
            mode='lines',
            name='Rejection Rate %',
            line=dict(color='#e74a3b', width=2, dash='dot'),
            yaxis='y2',
            opacity=0.7
        ))
    
    # Update layout with dark theme and dual y-axes
    fig.update_layout(
        title=dict(
            text='Hiring Trends & Rejection Rate (Last 3 Months)',
            x=0.5,
            xanchor='center',
            font=dict(size=16, family='Inter', color=text_color)
        ),
        xaxis=dict(
            title='Date',
            title_font=dict(size=12, family='Inter'),
            tickfont=dict(size=11, family='Inter'),
            gridcolor=grid_color,
            showline=True,
            linewidth=1,
            linecolor=grid_color,
            mirror=True
        ),
        yaxis=dict(
            title='Count',
            title_font=dict(size=12, family='Inter'),
            tickfont=dict(size=11, family='Inter'),
            gridcolor=grid_color,
            showline=True,
            linewidth=1,
            linecolor='#444',
            zerolinecolor='#444',
            showgrid=True
        ),
        yaxis2=dict(
            title='Rejection Rate (%)',
            overlaying='y',
            side='right',
            range=[0, 100],
            showgrid=False,
            showline=True,
            linewidth=1,
            linecolor='#e74a3b'
        ),
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=50, r=60, t=80, b=60),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#e5e7eb',
            borderwidth=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Inter, sans-serif'),
        hoverlabel=dict(
            bgcolor='#2d2d2d',
            font_size=12,
            font_family='Arial'
        )
    )
    
    return fig.to_html(full_html=False, config={'displayModeBar': False})