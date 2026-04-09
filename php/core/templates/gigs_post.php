<?php
/**
 * Post a new gig
 */
?>
<link rel="stylesheet" href="/static/css/osnova.css">

<div class="container">
    <h1>Post a Gig</h1>
    <p class="text-muted mb-3">Request help from your network</p>
    
    <form id="gig-form" class="card">
        <div class="form-group">
            <label>Title *</label>
            <input type="text" id="title" placeholder="e.g., Need lawn mowed" required>
        </div>
        
        <div class="form-group">
            <label>Description *</label>
            <textarea id="description" placeholder="Describe what you need done..." required></textarea>
        </div>
        
        <div class="form-group">
            <label>Price ($) *</label>
            <input type="number" id="price" placeholder="50" min="0" step="5" required>
        </div>
        
        <div class="form-group">
            <label>Location (optional)</label>
            <input type="text" id="location" placeholder="City or remote">
        </div>
        
        <div class="form-group">
            <label>Deadline (optional)</label>
            <input type="date" id="deadline">
        </div>
        
        <div class="form-group">
            <label>Who can see this?</label>
            <select id="ring-visibility">
                <option value="0">Ring 0 (closest friends)</option>
                <option value="1">Ring 1 (friends of friends)</option>
                <option value="2" selected>Ring 2 (extended network)</option>
                <option value="3">Public (anyone)</option>
            </select>
        </div>
        
        <button type="submit" class="btn btn-gig">Post Gig</button>
        <a href="/gigs" class="btn btn-secondary">Cancel</a>
    </form>
</div>

<script>
document.getElementById('gig-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        price: parseFloat(document.getElementById('price').value),
        location: document.getElementById('location').value,
        deadline: document.getElementById('deadline').value,
        ring_visibility: parseInt(document.getElementById('ring-visibility').value)
    };
    
    const response = await fetch('/api/gigs/post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    
    if (response.ok) {
        window.location.href = '/gigs';
    } else {
        alert('Failed to post gig. Please try again.');
    }
});
</script>
