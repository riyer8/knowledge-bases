import SwiftUI
import Foundation
import Combine

struct GraphWindowView: View {
    @StateObject private var graphStore = MarkdownGraphStore()
    @Environment(\.colorScheme) private var colorScheme
    @State private var selectedNodeID: String?
    @State private var dependencySourceID: String = ""
    @State private var dependencyTargetID: String = ""
    @State private var showControlsPanel = true
    @State private var showLogsPanel = true
    @State private var showOnlyOrphans = false
    @State private var showOnlyUnlinked = false
    @State private var selectedFolder = "All"
    private var isDarkMode: Bool { colorScheme == .dark }
    private var sidebarBackground: Color { isDarkMode ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fff1f8") }
    private var canvasBackground: Color { isDarkMode ? Color(nsColor: .underPageBackgroundColor) : Color(hex: "#fff7fb") }
    private var titleColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var selectedRowBackground: Color { isDarkMode ? Color.accentColor.opacity(0.25) : Color(hex: "#fce7f3") }
    private var cardBackground: Color { isDarkMode ? Color(nsColor: .windowBackgroundColor) : Color.white.opacity(0.55) }

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Image(systemName: "point.3.connected.trianglepath.dotted")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "#ec4899"))
                            .help("Knowledge graph overview")
                        Text("Knowledge Graph")
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .foregroundColor(titleColor)
                    }
                    Text("Browse markdown connections and filter by folder.")
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal, 10)
                .padding(.top, 8)

                HStack(spacing: 8) {
                    Button {
                        showControlsPanel.toggle()
                    } label: {
                        Label(showControlsPanel ? "Hide Controls" : "Show Controls", systemImage: "slider.horizontal.3")
                            .font(.system(size: 10, design: .rounded))
                    }
                    .buttonStyle(.bordered)
                    .help("Toggle graph controls")

                    Button {
                        showLogsPanel.toggle()
                    } label: {
                        Label(showLogsPanel ? "Hide Logs" : "Show Logs", systemImage: "list.bullet.rectangle")
                            .font(.system(size: 10, design: .rounded))
                    }
                    .buttonStyle(.bordered)
                    .help("Toggle file log list")
                }
                .padding(.horizontal, 10)

                if showControlsPanel {
                    VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Label("Controls", systemImage: "slider.horizontal.3")
                            .font(.system(size: 11, weight: .semibold, design: .rounded))
                            .foregroundColor(titleColor)
                            .help("Use these controls to filter and refresh")
                        Spacer()
                        if graphStore.isLoading {
                            ProgressView().scaleEffect(0.6)
                        }
                    }

                    HStack(spacing: 6) {
                        Button {
                            Task { await refreshGraph() }
                        } label: {
                            Label("Refresh", systemImage: "arrow.clockwise")
                                .font(.system(size: 10, design: .rounded))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)

                        Spacer()
                        Text("\(graphStore.graph.nodes.count) files")
                            .font(.system(size: 10, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                    }
                    .padding(10)
                    .background(RoundedRectangle(cornerRadius: 10).fill(cardBackground))
                    .padding(.horizontal, 10)

                    VStack(alignment: .leading, spacing: 6) {
                        Label("Create Dependency", systemImage: "link.badge.plus")
                            .font(.system(size: 11, weight: .semibold, design: .rounded))
                            .foregroundColor(titleColor)
                            .help("Connect one file to another manually")
                        Picker("Source", selection: $dependencySourceID) {
                            Text("From...").tag("")
                            ForEach(graphStore.graph.nodes, id: \.id) { node in
                                Text("\(node.label) • \(node.folder)").tag(node.id)
                            }
                        }
                        .font(.system(size: 10, design: .rounded))
                        Picker("Target", selection: $dependencyTargetID) {
                            Text("To...").tag("")
                            ForEach(graphStore.graph.nodes, id: \.id) { node in
                                Text("\(node.label) • \(node.folder)").tag(node.id)
                            }
                        }
                        .font(.system(size: 10, design: .rounded))
                        Button {
                            Task {
                                await graphStore.addDependency(source: dependencySourceID, target: dependencyTargetID)
                                await refreshGraph()
                            }
                        } label: {
                            Label("Add Dependency", systemImage: "link.badge.plus")
                                .font(.system(size: 10, design: .rounded))
                        }
                        .buttonStyle(.bordered)
                        .disabled(
                            dependencySourceID.isEmpty ||
                            dependencyTargetID.isEmpty ||
                            dependencySourceID == dependencyTargetID
                        )
                        Text("Tip: pick a source note and a target note, then add the edge.")
                            .font(.system(size: 10, design: .rounded))
                            .foregroundColor(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, 10)
                    .padding(.top, 2)
                    .padding(.bottom, 2)
                    .background(RoundedRectangle(cornerRadius: 10).fill(cardBackground))
                    .padding(.horizontal, 10)

                    Toggle("Orphans only", isOn: $showOnlyOrphans)
                        .font(.system(size: 10, design: .rounded))
                        .padding(.horizontal, 10)
                        .onChange(of: showOnlyOrphans) {
                            Task { await refreshGraph() }
                        }

                    Toggle("No outgoing links", isOn: $showOnlyUnlinked)
                        .font(.system(size: 10, design: .rounded))
                        .padding(.horizontal, 10)
                        .onChange(of: showOnlyUnlinked) {
                            Task { await refreshGraph() }
                        }

                    Picker("Folder", selection: $selectedFolder) {
                        Text("All").tag("All")
                        ForEach(graphStore.graph.folders, id: \.self) { folder in
                            Text(folder).tag(folder)
                        }
                    }
                    .font(.system(size: 10, design: .rounded))
                    .padding(.horizontal, 10)
                    .onChange(of: selectedFolder) {
                        Task { await refreshGraph() }
                    }
                }

                if let error = graphStore.errorMessage {
                    Text(error)
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.red.opacity(0.85))
                        .padding(.horizontal, 10)
                }

                if showLogsPanel {
                    List(graphStore.graph.nodes) { node in
                        Button {
                            selectedNodeID = node.id
                        } label: {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(node.label)
                                    .font(.system(size: 11, weight: .medium, design: .rounded))
                                    .lineLimit(1)
                                Text("in:\(node.incoming) out:\(node.outgoing)")
                                    .font(.system(size: 9, design: .rounded))
                                    .foregroundColor(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.vertical, 3)
                        }
                        .help("Click to highlight this node in graph")
                        .buttonStyle(.plain)
                        .listRowBackground(selectedNodeID == node.id ? selectedRowBackground : Color.clear)
                    }
                    .listStyle(.plain)
                }
            }
            .frame(width: 270)
            .background(sidebarBackground)

            Divider()

            GraphCanvasView(graph: graphStore.graph, highlightedID: selectedNodeID)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(canvasBackground)
                .clipped()
        }
        .task { await refreshGraph() }
    }

    private func refreshGraph() async {
        await graphStore.refresh(
            onlyOrphans: showOnlyOrphans,
            onlyUnlinked: showOnlyUnlinked,
            folder: selectedFolder == "All" ? nil : selectedFolder
        )
    }
}

private struct GraphCanvasView: View {
    let graph: MarkdownGraph
    let highlightedID: String?
    @Environment(\.colorScheme) private var colorScheme
    @State private var zoom: CGFloat = 1.0
    @State private var baseZoom: CGFloat = 1.0
    @State private var pan: CGSize = .zero
    @State private var basePan: CGSize = .zero
    @State private var nodeOffsets: [String: CGSize] = [:]
    @State private var nodeDragStart: [String: CGSize] = [:]
    @State private var nodeDragAllStart: [String: CGSize] = [:]
    @State private var isDraggingNode = false
    @State private var hoveredNodeID: String?
    private var isDarkMode: Bool { colorScheme == .dark }
    private var edgeColor: Color { isDarkMode ? Color.pink.opacity(0.45) : Color(hex: "#f9a8d4").opacity(0.45) }
    private var arrowColor: Color { isDarkMode ? Color.pink.opacity(0.85) : Color(hex: "#f472b6") }
    private var nodeTextColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var normalNodeColor: Color { isDarkMode ? Color.pink.opacity(0.8) : Color(hex: "#f472b6") }

    var body: some View {
        GeometryReader { geo in
            let nodes = makeNodes(in: geo.size)
            ZStack(alignment: .topTrailing) {
                ZStack {
                    ForEach(graph.edges) { edge in
                        if let source = nodes.first(where: { $0.id == edge.source }),
                           let target = nodes.first(where: { $0.id == edge.target }) {
                            let sourceOffset = nodeOffsets[source.id] ?? .zero
                            let targetOffset = nodeOffsets[target.id] ?? .zero
                            let sourcePoint = CGPoint(x: source.point.x + sourceOffset.width, y: source.point.y + sourceOffset.height)
                            let targetPoint = CGPoint(x: target.point.x + targetOffset.width, y: target.point.y + targetOffset.height)
                            Path { p in
                                p.move(to: sourcePoint)
                                p.addLine(to: targetPoint)
                            }
                            .stroke(colorForEdge(edge), lineWidth: hoveredNodeID == nil ? 1.0 : 1.2)
                            .opacity(opacityForEdge(edge))
                            drawArrowHead(from: sourcePoint, to: targetPoint)
                                .fill(colorForEdge(edge))
                                .opacity(opacityForEdge(edge))
                        }
                    }

                    ForEach(nodes, id: \.id) { node in
                        let offset = nodeOffsets[node.id] ?? .zero
                        VStack(spacing: 3) {
                            Circle()
                                .fill(colorForNode(nodeID: node.id))
                                .frame(width: node.id == highlightedID ? 16 : 11, height: node.id == highlightedID ? 16 : 11)
                            Text(node.label)
                                .font(.system(size: 9, weight: .medium, design: .rounded))
                                .foregroundColor(nodeTextColor)
                                .lineLimit(1)
                                .frame(width: 130)
                        }
                        .opacity(opacityForNode(nodeID: node.id))
                        .position(CGPoint(x: node.point.x + offset.width, y: node.point.y + offset.height))
                        .highPriorityGesture(
                            DragGesture(minimumDistance: 0)
                                .onChanged { value in
                                    isDraggingNode = true
                                    if nodeDragStart[node.id] == nil {
                                        nodeDragStart[node.id] = nodeOffsets[node.id] ?? .zero
                                    }
                                    if nodeDragAllStart.isEmpty {
                                        nodeDragAllStart = nodeOffsets
                                    }
                                    let start = nodeDragStart[node.id] ?? .zero
                                    let delta = CGSize(
                                        width: value.translation.width,
                                        height: value.translation.height
                                    )
                                    nodeOffsets[node.id] = CGSize(
                                        width: start.width + value.translation.width,
                                        height: start.height + value.translation.height
                                    )

                                    // Nudge directly connected nodes for a dynamic graph feel.
                                    let neighbors = directlyConnectedNodeIDs(for: node.id)
                                    withAnimation(.interactiveSpring(response: 0.22, dampingFraction: 0.82, blendDuration: 0.2)) {
                                        for neighborID in neighbors {
                                            let neighborStart = nodeDragAllStart[neighborID] ?? nodeOffsets[neighborID] ?? .zero
                                            nodeOffsets[neighborID] = CGSize(
                                                width: neighborStart.width + (delta.width * 0.28),
                                                height: neighborStart.height + (delta.height * 0.28)
                                            )
                                        }
                                    }
                                }
                                .onEnded { _ in
                                    nodeDragStart[node.id] = nil
                                    nodeDragAllStart.removeAll()
                                    isDraggingNode = false
                                }
                        )
                        .help("Drag node to reposition")
                    }

                    if nodes.isEmpty {
                        Text("No markdown files found.\nAdd .md files to build your graph.")
                            .multilineTextAlignment(.center)
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                }
                .scaleEffect(zoom, anchor: .topLeading)
                .offset(pan)
                .contentShape(Rectangle())
                .animation(.interactiveSpring(response: 0.22, dampingFraction: 0.9), value: pan)
                .animation(.interactiveSpring(response: 0.22, dampingFraction: 0.9), value: zoom)
                .simultaneousGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { value in
                            guard !isDraggingNode else { return }
                            pan = CGSize(
                                width: basePan.width + value.translation.width,
                                height: basePan.height + value.translation.height
                            )
                        }
                        .onEnded { value in
                            guard !isDraggingNode else { return }
                            basePan = CGSize(
                                width: basePan.width + value.translation.width,
                                height: basePan.height + value.translation.height
                            )
                            pan = basePan
                        }
                )
                .simultaneousGesture(
                    MagnificationGesture()
                        .onChanged { value in
                            zoom = max(0.35, min(4.0, baseZoom * value))
                        }
                        .onEnded { value in
                            baseZoom = max(0.35, min(4.0, baseZoom * value))
                            zoom = baseZoom
                        }
                )
                .onContinuousHover { phase in
                    switch phase {
                    case .active(let location):
                        updateHoveredNode(at: location, nodes: nodes)
                    case .ended:
                        hoveredNodeID = nil
                    }
                }

                HStack(spacing: 8) {
                    Button {
                        baseZoom = max(0.35, baseZoom - 0.15)
                        zoom = baseZoom
                    } label: {
                        Image(systemName: "minus.magnifyingglass")
                    }
                    .buttonStyle(.bordered)
                    .help("Zoom out")

                    Button {
                        baseZoom = min(4.0, baseZoom + 0.15)
                        zoom = baseZoom
                    } label: {
                        Image(systemName: "plus.magnifyingglass")
                    }
                    .buttonStyle(.bordered)
                    .help("Zoom in")

                    Button("Reset View") {
                        baseZoom = 1.0
                        zoom = 1.0
                        basePan = .zero
                        pan = .zero
                        nodeOffsets.removeAll()
                        nodeDragStart.removeAll()
                    }
                    .font(.system(size: 10, design: .rounded))
                    .buttonStyle(.bordered)
                    .help("Reset pan, zoom, and node positions")
                }
                .padding(8)
            }
            .padding(10)
        }
    }

    private func makeNodes(in size: CGSize) -> [GraphNode] {
        guard !graph.nodes.isEmpty else { return [] }
        let count = max(1, graph.nodes.count)
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let radius = max(46, min(size.width, size.height) / 2.6)

        return graph.nodes.enumerated().map { index, node in
            let angle = (Double(index) / Double(count)) * (Double.pi * 2.0)
            let point = CGPoint(
                x: center.x + CGFloat(cos(angle)) * radius,
                y: center.y + CGFloat(sin(angle)) * radius
            )
            let label = String(node.label.prefix(16))
            return GraphNode(id: node.id, point: point, label: label)
        }
    }

    private func drawArrowHead(from: CGPoint, to: CGPoint) -> Path {
        let dx = to.x - from.x
        let dy = to.y - from.y
        let angle = atan2(dy, dx)
        let headLength: CGFloat = 8
        let headAngle: CGFloat = .pi / 7

        let p1 = CGPoint(
            x: to.x - headLength * cos(angle - headAngle),
            y: to.y - headLength * sin(angle - headAngle)
        )
        let p2 = CGPoint(
            x: to.x - headLength * cos(angle + headAngle),
            y: to.y - headLength * sin(angle + headAngle)
        )
        var path = Path()
        path.move(to: to)
        path.addLine(to: p1)
        path.addLine(to: p2)
        path.closeSubpath()
        return path
    }

    private func updateHoveredNode(at location: CGPoint, nodes: [GraphNode]) {
        // Convert pointer from rendered space into graph-content space.
        let adjusted = CGPoint(
            x: (location.x - pan.width) / max(zoom, 0.0001),
            y: (location.y - pan.height) / max(zoom, 0.0001)
        )

        var bestNodeID: String?
        var bestDistance: CGFloat = .greatestFiniteMagnitude
        for node in nodes {
            let offset = nodeOffsets[node.id] ?? .zero
            let point = CGPoint(x: node.point.x + offset.width, y: node.point.y + offset.height)
            let dx = point.x - adjusted.x
            let dy = point.y - adjusted.y
            let distance = sqrt((dx * dx) + (dy * dy))
            if distance < bestDistance {
                bestDistance = distance
                bestNodeID = node.id
            }
        }

        // Snap hover only when cursor is near a node.
        if bestDistance <= 26, let bestNodeID {
            if hoveredNodeID != bestNodeID {
                hoveredNodeID = bestNodeID
            }
        } else {
            if hoveredNodeID != nil {
                hoveredNodeID = nil
            }
        }
    }

    private func directlyConnectedNodeIDs(for nodeID: String) -> Set<String> {
        var neighbors: Set<String> = []
        for edge in graph.edges {
            if edge.source == nodeID {
                neighbors.insert(edge.target)
            } else if edge.target == nodeID {
                neighbors.insert(edge.source)
            }
        }
        return neighbors
    }

    private enum HoverRelation {
        case focus
        case forward
        case backward
        case circular
        case other
        case none
    }

    private func relation(for nodeID: String) -> HoverRelation {
        guard let hovered = hoveredNodeID else { return .none }
        if nodeID == hovered { return .focus }
        let forward = Set(graph.edges.filter { $0.source == hovered }.map { $0.target })
        let backward = Set(graph.edges.filter { $0.target == hovered }.map { $0.source })
        let circular = forward.intersection(backward)
        if circular.contains(nodeID) { return .circular }
        if forward.contains(nodeID) { return .forward }
        if backward.contains(nodeID) { return .backward }
        return .other
    }

    private func colorForNode(nodeID: String) -> Color {
        switch relation(for: nodeID) {
        case .focus:
            return Color(hex: "#ec4899")
        case .forward:
            return Color(hex: "#22c55e")
        case .backward:
            return Color(hex: "#3b82f6")
        case .circular:
            return nodeID == highlightedID ? Color(hex: "#ec4899") : normalNodeColor
        case .other:
            return normalNodeColor
        case .none:
            return nodeID == highlightedID ? Color(hex: "#ec4899") : normalNodeColor
        }
    }

    private func opacityForNode(nodeID: String) -> Double {
        guard hoveredNodeID != nil else { return 1.0 }
        switch relation(for: nodeID) {
        case .other:
            return 0.25
        default:
            return 1.0
        }
    }

    private func colorForEdge(_ edge: GraphEdgeDTO) -> Color {
        guard let hovered = hoveredNodeID else { return edgeColor }
        let forward = Set(graph.edges.filter { $0.source == hovered }.map { $0.target })
        let backward = Set(graph.edges.filter { $0.target == hovered }.map { $0.source })
        let circular = forward.intersection(backward)

        if edge.source == hovered && circular.contains(edge.target) {
            return arrowColor
        }
        if edge.target == hovered && circular.contains(edge.source) {
            return arrowColor
        }
        if edge.source == hovered {
            return Color(hex: "#22c55e")
        }
        if edge.target == hovered {
            return Color(hex: "#3b82f6")
        }
        return edgeColor
    }

    private func opacityForEdge(_ edge: GraphEdgeDTO) -> Double {
        guard let hovered = hoveredNodeID else { return 1.0 }
        if edge.source == hovered || edge.target == hovered {
            return 1.0
        }
        let forward = Set(graph.edges.filter { $0.source == hovered }.map { $0.target })
        let backward = Set(graph.edges.filter { $0.target == hovered }.map { $0.source })
        let circular = forward.intersection(backward)
        if circular.contains(edge.source) && circular.contains(edge.target) {
            return 1.0
        }
        return 0.15
    }
}

private struct MarkdownGraph: Codable {
    var nodes: [GraphNodeDTO] = []
    var edges: [GraphEdgeDTO] = []
    var manualDependencies: [GraphEdgeDTO] = []
    var folders: [String] = []
}

private struct GraphNodeDTO: Codable, Identifiable {
    let id: String
    let label: String
    let path: String
    let folder: String
    let incoming: Int
    let outgoing: Int
    let degree: Int
    let isOrphan: Bool
    let isUnlinked: Bool
}

private struct GraphEdgeDTO: Codable, Identifiable {
    var id: String { "\(source)->\(target)" }
    let source: String
    let target: String
}

@MainActor
private final class MarkdownGraphStore: ObservableObject {
    @Published var graph = MarkdownGraph()
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!
    private struct AddDependencyRequest: Codable {
        let source: String
        let target: String
    }

    func refresh(onlyOrphans: Bool = false, onlyUnlinked: Bool = false, folder: String? = nil) async {
        isLoading = true
        defer { isLoading = false }
        do {
            var components = URLComponents(url: baseURL.appendingPathComponent("graph"), resolvingAgainstBaseURL: false)
            var items: [URLQueryItem] = [
                URLQueryItem(name: "orphans", value: onlyOrphans ? "1" : "0"),
                URLQueryItem(name: "unlinked", value: onlyUnlinked ? "1" : "0"),
            ]
            if let folder, !folder.isEmpty {
                items.append(URLQueryItem(name: "folder", value: folder))
            }
            components?.queryItems = items
            let requestURL = components?.url ?? baseURL.appendingPathComponent("graph")

            let (data, response) = try await URLSession.shared.data(from: requestURL)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            graph = try JSONDecoder().decode(MarkdownGraph.self, from: data)
            errorMessage = nil
        } catch {
            errorMessage = "Graph backend unavailable."
        }
    }

    func addDependency(source: String, target: String) async {
        guard !source.isEmpty, !target.isEmpty, source != target else { return }
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("graph/dependency"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(AddDependencyRequest(source: source, target: target))
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            errorMessage = nil
        } catch {
            errorMessage = "Failed to add dependency."
        }
    }
}

private struct GraphNode {
    let id: String
    let point: CGPoint
    let label: String
}
