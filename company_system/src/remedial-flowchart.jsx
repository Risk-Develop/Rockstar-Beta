import React, { useCallback } from 'react';
import ReactFlow, {
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Define the remedial action matrix data
const remedialMatrix = {
    ranges: {
        A: { name: 'Range A (Minor)', color: '#3B82F6', severity: 'low' },
        B: { name: 'Range B (Moderate)', color: '#EAB308', severity: 'medium' },
        C: { name: 'Range C (Serious)', color: '#F97316', severity: 'high' },
        D: { name: 'Range D (Severe)', color: '#EF4444', severity: 'critical' },
    },
    actions: {
        1: { A: 'Verbal Warning', B: 'Written Warning', C: 'Suspension 1-3 days', D: 'Dismissal' },
        2: { A: 'Written Warning', B: 'Suspension 1-3 days', C: 'Suspension 4-6 days', D: 'Dismissal' },
        3: { A: 'Suspension 1-3 days', B: 'Suspension 4-6 days', C: 'Dismissal', D: 'Dismissal' },
        4: { A: 'Suspension 4-6 days', B: 'Dismissal', C: 'Dismissal', D: 'Dismissal' },
        5: { A: 'Dismissal', B: 'Dismissal', C: 'Dismissal', D: 'Dismissal' },
    },
};

// Create initial nodes for the flowchart
const createNodes = () => {
    const nodes = [];
    const ranges = ['A', 'B', 'C', 'D'];
    const centerX = 400;
    const startY = 50;

    // Start node
    nodes.push({
        id: 'start',
        position: { x: centerX, y: startY },
        data: { label: '📋 New Violation Created' },
        type: 'input',
        style: {
            background: '#1e293b',
            color: '#fff',
            border: '2px solid #3B82F6',
            borderRadius: '8px',
            padding: '12px 20px',
            fontWeight: 'bold',
        },
    });

    // Count Offenses node
    nodes.push({
        id: 'count',
        position: { x: centerX, y: startY + 150 },
        data: { label: '🔢 Count Employee\'s\nExisting Violations' },
        style: {
            background: '#f0f9ff',
            color: '#0c4a6e',
            border: '2px solid #0ea5e9',
            borderRadius: '8px',
            padding: '12px 20px',
        },
    });

    // Offense count nodes (1-5)
    const offenseCounts = [1, 2, 3, 4, 5];
    offenseCounts.forEach((count, index) => {
        nodes.push({
            id: `offense-${count}`,
            position: { x: 80 + index * 160, y: startY + 320 },
            data: {
                label: `Offense #${count}`,
                count: count,
                badge: count === 1 ? '1st' : count === 2 ? '2nd' : count === 3 ? '3rd' : `${count}th`
            },
            style: {
                background: '#fef3c7',
                color: '#78350f',
                border: '2px solid #f59e0b',
                borderRadius: '8px',
                padding: '12px 20px',
                minWidth: '110px',
                textAlign: 'center',
            },
        });
    });

    // Range nodes
    ranges.forEach((range, index) => {
        const rangeInfo = remedialMatrix.ranges[range];
        nodes.push({
            id: `range-${range}`,
            position: { x: 80 + index * 220, y: startY + 520 },
            data: {
                label: `📊 Range ${range}\n${rangeInfo.name}`,
                range: range,
                color: rangeInfo.color
            },
            style: {
                background: `${rangeInfo.color}15`,
                color: rangeInfo.color,
                border: `3px solid ${rangeInfo.color}`,
                borderRadius: '12px',
                padding: '15px 20px',
                minWidth: '160px',
            },
        });
    });

    // Action nodes - placed in rows for each range
    ranges.forEach((range, rangeIndex) => {
        const rangeInfo = remedialMatrix.ranges[range];

        // Single row of actions
        for (let count = 1; count <= 5; count++) {
            const action = remedialMatrix.actions[count]?.[range];
            if (action) {
                nodes.push({
                    id: `action-${range}-${count}`,
                    position: {
                        x: 20 + rangeIndex * 240 + (count - 1) * 65,
                        y: startY + 720
                    },
                    data: {
                        label: `${count}. ${action}`,
                        count: count,
                        range: range,
                        action: action,
                        isDismissal: action === 'Dismissal'
                    },
                    style: {
                        background: action === 'Dismissal' ? '#fef2f2' : '#f0fdf4',
                        color: action === 'Dismissal' ? '#991b1b' : '#166534',
                        border: `2px solid ${action === 'Dismissal' ? '#ef4444' : '#22c55e'}`,
                        borderRadius: '6px',
                        padding: '10px 14px',
                        fontSize: '11px',
                        maxWidth: '150px',
                        whiteSpace: 'nowrap',
                    },
                });
            }
        }
    });

    // End node
    nodes.push({
        id: 'end',
        position: { x: centerX - 50, y: startY + 900 },
        data: { label: '✅ Violation Saved\nWith Action Applied' },
        type: 'output',
        style: {
            background: '#166534',
            color: '#fff',
            border: '2px solid #22c55e',
            borderRadius: '8px',
            padding: '12px 20px',
        },
    });

    return nodes;
};

// Create edges
const createEdges = () => {
    const edges = [];

    // Start to Count
    edges.push({
        id: 'start-count',
        source: 'start',
        target: 'count',
        animated: true,
        style: { stroke: '#3B82F6', strokeWidth: 2 },
    });

    // Count to offense nodes
    const offenseCounts = [1, 2, 3, 4, 5];
    offenseCounts.forEach((count) => {
        edges.push({
            id: `count-offense-${count}`,
            source: 'count',
            target: `offense-${count}`,
            animated: true,
            style: { stroke: '#f59e0b', strokeWidth: 2 },
            label: count === 1 ? '1st' : count === 2 ? '2nd' : count === 3 ? '3rd' : `${count}th`,
            labelStyle: { fill: '#78350f', fontWeight: 'bold' },
        });
    });

    // Connect offense nodes to range nodes
    const rangeMapping = {
        1: 'A',
        2: 'B',
        3: 'C',
        4: 'D',
        5: 'D',
    };

    offenseCounts.forEach((count) => {
        const targetRange = rangeMapping[count];
        edges.push({
            id: `offense-${count}-range-${targetRange}`,
            source: `offense-${count}`,
            target: `range-${targetRange}`,
            animated: true,
            style: {
                stroke: remedialMatrix.ranges[targetRange].color,
                strokeWidth: 3
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: remedialMatrix.ranges[targetRange].color,
            },
        });
    });

    // Connect ranges to actions
    ['A', 'B', 'C', 'D'].forEach((range) => {
        for (let count = 1; count <= 5; count++) {
            const action = remedialMatrix.actions[count]?.[range];
            if (action) {
                edges.push({
                    id: `range-${range}-action-${count}`,
                    source: `range-${range}`,
                    target: `action-${range}-${count}`,
                    style: {
                        stroke: remedialMatrix.ranges[range].color,
                        strokeWidth: 2,
                        opacity: 0.6
                    },
                });
            }
        }
    });

    // Connect actions to end
    ['A', 'B', 'C', 'D'].forEach((range) => {
        for (let count = 1; count <= 5; count++) {
            const action = remedialMatrix.actions[count]?.[range];
            if (action) {
                edges.push({
                    id: `action-${range}-${count}-end`,
                    source: `action-${range}-${count}`,
                    target: 'end',
                    animated: true,
                    style: { stroke: '#22c55e', strokeWidth: 2 },
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        color: '#22c55e',
                    },
                });
            }
        }
    });

    return edges;
};

// Custom node component for better styling
const CustomNode = ({ data }) => {
    return (
        <div style={{ textAlign: 'center' }}>
            <div style={{
                whiteSpace: 'pre-wrap',
                fontSize: '12px',
                fontWeight: '600',
                lineHeight: '1.4'
            }}>
                {data.label}
            </div>
        </div>
    );
};

const nodeTypes = {
    custom: CustomNode,
};

export default function RemedialActionFlowchart() {
    const [nodes, setNodes, onNodesChange] = useNodesState(createNodes());
    const [edges, setEdges, onEdgesChange] = useEdgesState(createEdges());

    const onConnect = useCallback(
        (params) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    return (
        <div style={{ width: '100%', height: '950px', border: '2px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                attributionPosition="bottom-left"
            >
                <Controls
                    style={{
                        background: '#fff',
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb'
                    }}
                />
                <Background
                    color="#94a3b8"
                    gap={20}
                    size={1}
                    style={{ background: '#f8fafc' }}
                />
            </ReactFlow>
        </div>
    );
}