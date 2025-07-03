import json
import sys

def analyze_edge_compatibility(json_file_path):
    """Analyze puzzle pieces for edge compatibility issues"""
    
    # Load the puzzle data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pieces = data['pieces']
    print(f"Analyzing {len(pieces)} puzzle pieces for edge compatibility...")
    print("=" * 60)
    
    # Check for adjacent pieces with incompatible edges
    incompatible_pairs = []
    tolerance = 5  # Allow small positioning differences
    
    for i, piece_a in enumerate(pieces):
        for j, piece_b in enumerate(pieces):
            if i >= j:  # Avoid duplicate checks
                continue
                
            # Get positions and dimensions
            a_x, a_y = piece_a['x'], piece_a['y']
            a_w, a_h = piece_a['width'], piece_a['height']
            b_x, b_y = piece_b['x'], piece_b['y']
            b_w, b_h = piece_b['width'], piece_b['height']
            
            # Check if pieces are horizontally adjacent (A is left of B)
            if (abs((a_x + a_w) - b_x) < tolerance and 
                abs(a_y - b_y) < tolerance and 
                abs(a_h - b_h) < tolerance):
                
                a_right = piece_a['edges']['right']
                b_left = piece_b['edges']['left']
                
                if not are_edges_compatible(a_right, b_left):
                    incompatible_pairs.append({
                        'piece_a': piece_a['id'],
                        'piece_b': piece_b['id'],
                        'position': 'horizontal',
                        'a_edge': f"right={a_right}",
                        'b_edge': f"left={b_left}",
                        'issue': f"Both edges are '{a_right}'" if a_right == b_left else f"Incompatible: {a_right} vs {b_left}"
                    })
            
            # Check if pieces are vertically adjacent (A is above B)
            elif (abs((a_y + a_h) - b_y) < tolerance and 
                  abs(a_x - b_x) < tolerance and 
                  abs(a_w - b_w) < tolerance):
                
                a_bottom = piece_a['edges']['bottom']
                b_top = piece_b['edges']['top']
                
                if not are_edges_compatible(a_bottom, b_top):
                    incompatible_pairs.append({
                        'piece_a': piece_a['id'],
                        'piece_b': piece_b['id'],
                        'position': 'vertical',
                        'a_edge': f"bottom={a_bottom}",
                        'b_edge': f"top={b_top}",
                        'issue': f"Both edges are '{a_bottom}'" if a_bottom == b_top else f"Incompatible: {a_bottom} vs {b_top}"
                    })
    
    # Report findings
    if incompatible_pairs:
        print(f"❌ Found {len(incompatible_pairs)} incompatible edge pairs:")
        print()
        
        for pair in incompatible_pairs:
            print(f"🔴 {pair['piece_a']} ↔ {pair['piece_b']} ({pair['position']})")
            print(f"   {pair['piece_a']}.{pair['a_edge']} | {pair['piece_b']}.{pair['b_edge']}")
            print(f"   Issue: {pair['issue']}")
            print()
            
        # Show specific examples from the issue description
        print("=" * 60)
        print("SPECIFIC EXAMPLES FROM ISSUE DESCRIPTION:")
        print()
        
        piece_0 = next(p for p in pieces if p['id'] == 'piece_0')
        piece_1 = next(p for p in pieces if p['id'] == 'piece_1')
        
        print(f"piece_0 (x:{piece_0['x']}, y:{piece_0['y']}) edges: {piece_0['edges']}")
        print(f"piece_1 (x:{piece_1['x']}, y:{piece_1['y']}) edges: {piece_1['edges']}")
        print()
        print(f"piece_0.right = '{piece_0['edges']['right']}'")
        print(f"piece_1.left = '{piece_1['edges']['left']}'")
        print(f"Both are '{piece_0['edges']['right']}' - this creates a gap!")
        
    else:
        print("✅ All adjacent pieces have compatible edges!")
    
    return len(incompatible_pairs)

def are_edges_compatible(edge1, edge2):
    """Check if two edges are compatible (one tab, one blank)"""
    if edge1 == 'flat' or edge2 == 'flat':
        return True  # Flat edges are always compatible
    
    # For tab/blank edges, they must be complementary
    return (edge1 == 'tab' and edge2 == 'blank') or (edge1 == 'blank' and edge2 == 'tab')

if __name__ == "__main__":
    json_file = "logs\\API에서 받은 원본 데이터.json"
    
    try:
        incompatible_count = analyze_edge_compatibility(json_file)
        
        if incompatible_count > 0:
            print("=" * 60)
            print("CONCLUSION: Edge compatibility issues found!")
            print("This confirms the problem described in the issue.")
            print("Adjacent pieces cannot connect properly due to incompatible edges.")
        else:
            print("No edge compatibility issues found.")
            
    except Exception as e:
        print(f"Error analyzing puzzle data: {e}")
        sys.exit(1)