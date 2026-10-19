function pa_probe2()
PAI_ROOT = strrep(fileparts(fileparts(mfilename('fullpath'))), '\', '/');
S = load([PAI_ROOT '/results/wire/W1_single/W1_results.mat']);
fn = fieldnames(S.IM);
g = S.grid;
fprintf('grid: x[%.2f %.2f] y[%.2f %.2f] dx=%.4f\n', g.x(1), g.x(end), g.y(1), g.y(end), g.dx);
for i = 1:numel(fn)
    A = S.IM.(fn{i});
    [v, k] = max(A(:)); [iy, ix] = ind2sub(size(A), k);
    p = prctile(A(:), [50 90 99 99.9 99.99]);
    fprintf('%-6s max=%.4g @(x=%.2f,y=%.2f,idx %d,%d) | p50=%.3g p90=%.3g p99=%.3g p99.9=%.3g p99.99=%.3g\n', ...
        fn{i}, v, g.x(ix), g.y(iy), ix, iy, p(1),p(2),p(3),p(4),p(5));
end
A = S.IM.env2; [~,k] = max(A(:)); [iy, ix] = ind2sub(size(A), k);
w = round(2/g.dx);
sub = A(max(1,iy-w):min(end,iy+w), max(1,ix-w):min(end,ix+w));
sv = sort(sub(:), 'descend');
fprintf('env2 峰值邻域 %dx%d: 次大/最大 = %.4f\n', size(sub,1), size(sub,2), sv(2)/sv(1));
end
