import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="FlightIQ ULTIMATE v2.0", layout="wide", page_icon="✈️")

st.markdown("# ✈️ FlightIQ ULTIMATE v2.0")
st.markdown("### AI-Powered Flight Intelligence & Route Optimization")

BACKEND = "http://backend:8000"

# Sidebar
st.sidebar.title("🎯 Navigation")
page = st.sidebar.radio(
    "Select Feature",
    ["🔍 Smart Search", "💡 Recommendations", "🛫 Route Optimizer", "📊 Analytics"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**FlightIQ ULTIMATE v2.0**

✅ Semantic Search with Preferences
✅ AI-Powered Recommendations  
✅ Path Optimization (Dijkstra)
✅ Multi-Criteria Route Scoring
✅ Network Analytics

🆓 Zero API Costs | 🚀 Sub-10ms Search
""")

# ===================== SMART SEARCH PAGE =====================
if page == "🔍 Smart Search":
    st.header("🔍 Intelligent Airport Search")
    st.info("💡 Use natural language with preference filters. Try: 'budget-friendly hubs in Asia'")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Search Query", 
            placeholder="e.g., tropical islands, business hubs, budget-friendly airports",
            key="search_query"
        )
    with col2:
        limit = st.number_input("Results", 5, 50, 10)
    
    # Preference filters
    st.subheader("🎚️ Preference Filters (Optional)")
    col1, col2 = st.columns(2)
    with col1:
        price_tier = st.selectbox(
            "Price Tier",
            ["Any", "budget-friendly", "moderate", "premium", "luxury"]
        )
    with col2:
        hub_type = st.selectbox(
            "Hub Type",
            ["Any", "small", "connector", "regional-hub", "major-hub"]
        )
    
    if st.button("🔍 Search with AI", type="primary"):
        preferences = {}
        if price_tier != "Any":
            preferences["price_tier"] = price_tier
        if hub_type != "Any":
            preferences["hub_type"] = hub_type
        
        payload = {
            "query": query,
            "limit": limit,
            "preferences": preferences if preferences else None
        }
        
        with st.spinner("🤖 AI is analyzing your search..."):
            r = requests.post(f"{BACKEND}/api/v1/search/airports", json=payload).json()
            results = r.get("results", [])
            
            if results:
                st.success(f"✅ Found {len(results)} airports matching your criteria")
                
                # Map visualization
                df = pd.DataFrame(results)
                
                # Build hover_data dynamically based on available columns
                hover_data = {
                    "city": True,
                    "country": True,
                    "iata_code": True,
                    "latitude": False,
                    "longitude": False
                }
                
                # Add optional columns if they exist
                if "hub_type" in df.columns:
                    hover_data["hub_type"] = True
                if "price_tier" in df.columns:
                    hover_data["price_tier"] = True
                if "score" in df.columns:
                    hover_data["score"] = ":.3f"
                
                fig = px.scatter_mapbox(
                    df, 
                    lat="latitude", 
                    lon="longitude",
                    hover_name="name",
                    hover_data=hover_data,
                    color="price_tier" if "price_tier" in df.columns else None,
                    size="annual_passengers" if "annual_passengers" in df.columns else None,
                    zoom=2,
                    height=500
                )
                fig.update_layout(mapbox_style="open-street-map")
                st.plotly_chart(fig, use_container_width=True)
                
                # Data table - only show columns that exist
                display_cols = ['name', 'city', 'country', 'iata_code']
                
                # Add optional columns if they exist
                if 'hub_type' in df.columns:
                    display_cols.append('hub_type')
                if 'price_tier' in df.columns:
                    display_cols.append('price_tier')
                if 'score' in df.columns:
                    display_cols.append('score')
                if 'annual_passengers' in df.columns:
                    df['passengers'] = df['annual_passengers'].apply(lambda x: f"{x:,}" if pd.notna(x) else "N/A")
                    display_cols.append('passengers')
                
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.warning("No results found. Try adjusting your query or preferences.")

# ===================== RECOMMENDATIONS PAGE =====================
elif page == "💡 Recommendations":
    st.header("💡 Personalized Recommendations")
    
    tab1, tab2, tab3 = st.tabs(["🎯 By Preferences", "🔄 Similar Airports", "🛫 Route Suggestions"])
    
    with tab1:
        st.subheader("Find Airports by Your Preferences")
        col1, col2 = st.columns(2)
        with col1:
            pref_hub = st.selectbox("Hub Type", ["Any", "small", "connector", "regional-hub"], key="pref_hub")
            pref_price = st.selectbox("Price Tier", ["Any", "budget-friendly", "moderate", "premium", "luxury"], key="pref_price")
        with col2:
            pref_country = st.text_input("Country (optional)", key="pref_country")
            pref_limit = st.number_input("Number of Results", 5, 50, 10, key="pref_limit")
        
        if st.button("🎯 Get Recommendations", type="primary"):
            prefs = {}
            if pref_hub != "Any":
                prefs["hub_type"] = pref_hub
            if pref_price != "Any":
                prefs["price_tier"] = pref_price
            if pref_country:
                prefs["country"] = pref_country
            
            with st.spinner("Finding perfect matches..."):
                r = requests.post(
                    f"{BACKEND}/api/v1/recommend/by-preferences",
                    json={"preferences": prefs, "limit": pref_limit}
                ).json()
                
                results = r.get("results", [])
                if results:
                    df = pd.DataFrame(results)
                    
                    # Display cards
                    for idx, row in df.head(5).iterrows():
                        with st.expander(f"✈️ {row['name']} ({row['iata_code']}) - {row['city']}, {row['country']}"):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Hub Type", row['hub_type'])
                            col2.metric("Price Tier", row['price_tier'])
                            if 'annual_passengers' in row:
                                col3.metric("Annual Passengers", f"{int(row['annual_passengers']):,}")
                            if 'facilities' in row and row['facilities']:
                                st.write("**Facilities:**", row['facilities'])
                else:
                    st.info("No airports match your exact preferences. Try broadening your criteria.")
    
    with tab2:
        st.subheader("Find Airports Similar to...")
        airport_id = st.number_input("Enter Airport ID", min_value=1, value=3797, help="e.g., 3797 for JFK")
        sim_limit = st.number_input("Number of Similar Airports", 5, 20, 10, key="sim_limit")
        
        if st.button("🔄 Find Similar", type="primary"):
            with st.spinner("Calculating similarity scores..."):
                r = requests.get(f"{BACKEND}/api/v1/recommend/similar-airports/{airport_id}?limit={sim_limit}").json()
                results = r.get("results", [])
                
                if results:
                    df = pd.DataFrame(results)
                    st.dataframe(
                        df[['name', 'city', 'country', 'hub_type', 'price_tier', 'similarity_score']],
                        use_container_width=True
                    )
                else:
                    st.warning("No similar airports found.")
    
    with tab3:
        st.subheader("Route Suggestions from Airport")
        route_airport_id = st.number_input("Airport ID", min_value=1, value=3797, key="route_airport")
        route_price = st.selectbox("Prefer Price Tier", ["Any", "budget-friendly", "moderate", "premium", "luxury"], key="route_price")
        route_limit = st.number_input("Number of Routes", 5, 20, 10, key="route_limit")
        
        if st.button("🛫 Get Route Suggestions", type="primary"):
            price_param = f"?price_tier={route_price}&limit={route_limit}" if route_price != "Any" else f"?limit={route_limit}"
            with st.spinner("Finding best routes..."):
                r = requests.get(f"{BACKEND}/api/v1/recommend/routes-from/{route_airport_id}{price_param}").json()
                results = r.get("results", [])
                
                if results:
                    for route in results[:5]:
                        st.markdown(f"""
                        **✈️ {route['source_name']} ({route['source_iata']}) → {route['dest_name']} ({route['dest_iata']})**
                        - Distance: {route['distance_km']:.0f} km
                        - Destination: {route['dest_city']}, {route['dest_country']}
                        - Airlines: {route['num_airlines']}
                        - Price Tier: {route['price_tier']}
                        """)
                        st.markdown("---")
                else:
                    st.info("No routes found from this airport.")

# ===================== ROUTE OPTIMIZER PAGE =====================
elif page == "🛫 Route Optimizer":
    st.header("🛫 AI-Powered Route Optimization")
    st.info("💡 Uses Dijkstra's algorithm with MariaDB recursive CTEs for optimal pathfinding")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        source = st.text_input("From (IATA Code)", value="SSC", placeholder="e.g., JFK").upper()
    with col2:
        dest = st.text_input("To (IATA Code)", value="WUH", placeholder="e.g., LAX").upper()
    with col3:
        max_stops = st.number_input("Max Stops", 1, 5, 2)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 Find Optimal Route", type="primary"):
            with st.spinner("🧠 AI is calculating optimal path..."):
                r = requests.get(
                    f"{BACKEND}/api/v1/optimize/route",
                    params={"source": source, "dest": dest, "max_stops": max_stops, "criteria": "distance"}
                ).json()
                
                if r.get("success"):
                    opt = r["optimal_path"]
                    
                    # Summary
                    st.success("✅ Optimal Route Found!")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Distance", f"{opt['total_distance_km']:.0f} km")
                    col2.metric("Stops", opt['stops'])
                    col3.metric("Est. Time", f"{opt['estimated_time_hours']:.1f} hours")
                    
                    # Route details
                    st.subheader("📍 Route Details")
                    for leg in opt['route_details']:
                        st.markdown(f"""
                        **Leg {leg['leg']}: {leg['from']['city']} → {leg['to']['city']}**
                        - From: {leg['from']['name']} ({leg['from']['iata']}), {leg['from']['country']}
                        - To: {leg['to']['name']} ({leg['to']['iata']}), {leg['to']['country']}
                        - Distance: {leg['distance_km']:.0f} km
                        - Airline: {leg['airline']}
                        """)
                    
                    # Alternative paths
                    if r.get("alternative_paths"):
                        st.subheader("🔄 Alternative Routes")
                        for idx, alt in enumerate(r["alternative_paths"], 1):
                            with st.expander(f"Alternative {idx}: {alt['total_distance_km']:.0f} km, {alt['stops']} stops"):
                                for leg in alt['route_details']:
                                    st.write(f"• {leg['from']['iata']} → {leg['to']['iata']} ({leg['distance_km']:.0f} km)")
                else:
                    st.error(f"❌ {r.get('error', 'No route found')}")
    
    with col2:
        if st.button("⚖️ Multi-Criteria Optimization"):
            with st.spinner("🧮 Analyzing multiple optimization criteria..."):
                r = requests.get(
                    f"{BACKEND}/api/v1/optimize/multi-criteria",
                    params={"source": source, "dest": dest, "max_stops": max_stops}
                ).json()
                
                if r.get("success") and r.get("recommended_path"):
                    rec = r["recommended_path"]
                    st.success("✅ Best Overall Route (Multi-Criteria)")
                    st.metric("Optimization Score", rec['score'])
                    st.metric("Distance", f"{rec['total_distance_km']:.0f} km")
                    st.metric("Stops", rec['stops'])
                    
                    if r.get("all_paths") and len(r["all_paths"]) > 1:
                        st.write("**All Paths Ranked:**")
                        df = pd.DataFrame([{
                            'Rank': idx + 1,
                            'Distance (km)': p['total_distance_km'],
                            'Stops': p['stops'],
                            'Time (hrs)': p['estimated_time_hours'],
                            'Score': p['score']
                        } for idx, p in enumerate(r["all_paths"])])
                        st.dataframe(df, use_container_width=True)
                else:
                    st.error("❌ No route found")

# ===================== ANALYTICS PAGE =====================
else:
    st.header("📊 Advanced Network Analytics")
    
    # Network Overview
    st.subheader("🌐 Network Overview")
    with st.spinner("Loading network statistics..."):
        stats = requests.get(f"{BACKEND}/api/v1/analytics/network-stats").json()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✈️ Total Airports", f"{stats.get('total_airports', 0):,}")
    col2.metric("🛫 Total Routes", f"{stats.get('total_routes', 0):,}")
    col3.metric("🏢 Airlines", stats.get('total_airlines', 0))
    col4.metric("🌏 Major Hubs", stats.get('major_hubs', 0))
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📏 Avg Distance", f"{stats.get('avg_route_distance_km', 0):.0f} km")
    col2.metric("🛣️ Max Distance", f"{stats.get('max_route_distance_km', 0):.0f} km")
    col3.metric("💰 Budget Airports", f"{stats.get('budget_friendly_airports', 0):,}")
    
    st.markdown("---")
    
    # Hub Analysis
    st.subheader("🏢 Hub Airport Analysis")
    hub_filter = st.selectbox("Filter by Hub Type", ["All", "small", "connector", "regional-hub", "major-hub"])
    hub_limit = st.number_input("Number of Hubs", 10, 100, 20, key="hub_limit")
    
    if st.button("📊 Analyze Hubs"):
        params = {"limit": hub_limit}
        if hub_filter != "All":
            params["hub_type"] = hub_filter
        
        with st.spinner("Analyzing hub airports..."):
            r = requests.get(f"{BACKEND}/api/v1/analytics/hub-airports", params=params).json()
            results = r.get("results", [])
            
            if results:
                df = pd.DataFrame(results)
                
                # Bar chart
                fig = px.bar(
                    df.head(15),
                    x='name',
                    y='num_destinations',
                    color='hub_type',
                    title="Top Airports by Number of Destinations",
                    labels={'num_destinations': 'Direct Destinations', 'name': 'Airport'}
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Data table
                st.dataframe(df, use_container_width=True)
    
    st.markdown("---")
    
    # Busiest Routes
    st.subheader("🔥 Busiest Routes")
    route_limit = st.number_input("Number of Routes", 5, 50, 10, key="route_limit")
    
    if st.button("🔍 Show Busiest Routes"):
        with st.spinner("Analyzing route traffic..."):
            r = requests.get(f"{BACKEND}/api/v1/analytics/busiest-routes", params={"limit": route_limit}).json()
            results = r.get("results", [])
            
            if results:
                for idx, route in enumerate(results, 1):
                    st.markdown(f"""
                    **{idx}. {route['source_name']} ({route['source_iata']}) ↔ {route['dest_name']} ({route['dest_iata']})**
                    - Airlines: **{route['num_airlines']}**
                    - Distance: {route['avg_distance_km']:.0f} km
                    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**💻 FlightIQ ULTIMATE v2.0**")
st.sidebar.markdown("Built with MariaDB + Ollama + Streamlit")
