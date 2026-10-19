function pa_probe()
PAI_ROOT = strrep(fileparts(fileparts(mfilename('fullpath'))), '\', '/');
g.x = linspace(-20,20,401);  g.y = linspace(-20,20,401);
IMs = struct(); IMs.env = rand(401); IMs.env2 = rand(401);
grid = g;  meths = {'env','env2'};
names = {'D1  线性包络 |z|','D1^2  包络平方（既有主方法）'};
cols = [0 0.35 0.8; 0.85 0.1 0.1];  nm = 2;
out = [PAI_ROOT '/results/_probe.png'];
f = figure('Visible','off','Color','w','Position',[50 50 600 340]);
run1(@() tiledlayout(f, 1, nm, 'TileSpacing','compact','Padding','compact'), 'tiledlayout_f');
tl = tiledlayout(f, 1, nm, 'TileSpacing','compact','Padding','compact');
ax = nexttile(tl); fprintf('nexttile ok\n');
run1(@() imagesc(ax, grid.x, grid.y, IMs.(meths{1})), 'imagesc');
run1(@() axis(ax,'image'), 'axis');
run1(@() set(ax,'YDir','normal'), 'YDir');
run1(@() colormap(ax, hot), 'colormap');
run1(@() clim(ax, [0 1]), 'clim');
run1(@() xlabel(ax,'x (mm)'), 'xlabel');
run1(@() ylabel(ax,'y (mm)'), 'ylabel');
run1(@() title(ax, names{1}, 'Color', cols(1,:), 'FontSize', 9, 'FontWeight','bold'), 'title');
run1(@() sgtitle(f, 'abc', 'FontWeight','bold'), 'sgtitle');
cb = colorbar(tl); fprintf('colorbar(tl) ok\n');
run1(@() setfield(struct(), 'x', 1), 'noop');
try, cb.Layout.Tile = 'east'; fprintf('cb.Tile ok\n'); catch e, fprintf('FAIL cb.Tile : %s\n', e.message); end
try, cb.Label.String = 'x'; fprintf('cb.Label ok\n'); catch e, fprintf('FAIL cb.Label : %s\n', e.message); end
run1(@() exportgraphics(f, out, 'Resolution', 200), 'exportgraphics');
end
function run1(fn, tag)
try, fn(); fprintf('OK   %s\n', tag); catch e, fprintf('FAIL %s : %s\n', tag, e.message); end
end
